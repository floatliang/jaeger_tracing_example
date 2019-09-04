
import functools

from opentracing import Format, tags
from opentracing.scope_managers.asyncio import AsyncioScopeManager
from jaeger_client import Config
from flask import request


class EmptyScope(object):
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class EmptyTracer(object):
    @property
    def active_span(self):
        return None


class FlaskTracer(object):

    def __init__(self, config, metrics=None, service_name=None, metrics_factory=None,
                 validate=False, is_async=False, enabled=True):
        if config is None:
            raise AttributeError("config cannot be empty")

        self.enabled = enabled
        if self.enabled:
            config = Config(config, metrics=metrics, service_name=service_name,
                            metrics_factory=metrics_factory, validate=validate,
                            scope_manager=AsyncioScopeManager() if is_async else None)
            self.tracer = config.initialize_tracer()
        else:
            self.tracer = EmptyTracer()

    def start_span(self, operation_name=None, child_of=None,
                   references=None, tags=None, start_time=None,
                   ignore_active_span=False):
        return self.tracer.start_span(operation_name=operation_name, child_of=child_of,
                                      references=references, tags=tags, start_time=start_time,
                                      ignore_active_span=ignore_active_span)

    def start_active_span(self, operation_name=None, child_of=None,
                          references=None, tags=None, start_time=None,
                          ignore_active_span=False, finish_on_close=True):
        return self.tracer.start_active_span(operation_name=operation_name, child_of=child_of,
                                             references=references, tags=tags, start_time=start_time,
                                             ignore_active_span=ignore_active_span,
                                             finish_on_close=finish_on_close)

    def inject(self, span_context, format, carrier):
        self.tracer.inject(span_context=span_context, format=format, carrier=carrier)

    def extract(self, format, carrier):
        return self.tracer.extract(format=format, carrier=carrier)

    def close(self):
        self.tracer.close()

    def _before_request(self, request_name):
        headers = {}
        for k, v in request.headers:
            headers[k.lower()] = v
        request_name = request.path + '/' + str(request_name) if request.path else \
            '/' + str(request_name)

        try:
            parent_ctx = self.extract(Format.HTTP_HEADERS, headers)
            scope = self.start_active_span(operation_name=request_name, child_of=parent_ctx)
        except Exception as ex:
            scope = self.start_active_span(operation_name=request_name)
            scope.span.set_tag('trace_error', str(ex))

        scope.span.set_tag(tags.SPAN_KIND, tags.SPAN_KIND_RPC_SERVER)
        scope.span.set_baggage_item('path', request_name)

    def _after_request(self, error=None):
        scope = self.tracer.scope_manager.active
        if scope is None:
            return

        if error is not None:
            scope.span.log_kv({
                'event': tags.ERROR,
                'message': error
            })

        scope.close()

    def _before_function(self, function_name, skipped=True):

        if self.tracer.active_span or not skipped:
            span = self.tracer.active_span
            path = span.get_baggage_item('path') if span else ''
            function_name = path + '/' + function_name if path else '/' + function_name
            scope = self.start_active_span(operation_name=function_name)
        else:
            return False

        scope.span.set_tag(tags.SPAN_KIND, 'function')
        scope.span.set_baggage_item('path', function_name)
        return True

    def _after_function(self, error=None):
        scope = self.tracer.scope_manager.active

        if scope is None:
            return

        if error is not None:
            scope.span.log_kv({
                'event': tags.ERROR,
                'message': error
            })

        scope.close()

    def trace_inbound_request(self, request_name=None):
        def wrapper(func):
            if not self.enabled:
                return func

            @functools.wraps(func)
            def wrapped(*args, **kwargs):
                nonlocal request_name
                if request_name is None:
                    request_name = func.__name__ or "unknown_re"
                error = None
                self._before_request(request_name)
                try:
                    r = func(*args, **kwargs)
                except Exception as ex:
                    error = ex
                self._after_request(error=error)
                if error:
                    raise error
                return r

            return wrapped

        return wrapper

    def trace_function(self, function_name=None, skipped=True):
        def wrapper(func):
            if not self.enabled:
                return func

            @functools.wraps(func)
            def wrapped(*args, **kwargs):
                nonlocal function_name
                if function_name is None:
                    function_name = func.__name__ or "unknown_func"
                error = None
                if self._before_function(function_name, skipped):
                    try:
                        r = func(*args, **kwargs)
                    except Exception as ex:
                        error = ex
                    self._after_function(error=error)
                    if error:
                        raise error
                else:
                    r = func(*args, **kwargs)
                return r

            return wrapped

        return wrapper

    def trace_operation(self, operation_name=None, parent_ctx=None, skipped=False):
        if not self.enabled:
            return EmptyScope()

        if not operation_name:
            operation_name = 'unknown_op'
        if parent_ctx:
            operation_name = '/' + operation_name
            scope = self.start_active_span(operation_name=operation_name, child_of=parent_ctx)
        elif self.tracer.active_span or not skipped:
            span = self.tracer.active_span
            path = span.get_baggage_item('path') if span else ''
            operation_name = path + '/' + operation_name if path else '/' + operation_name
            scope = self.start_active_span(operation_name=operation_name)
        else:
            return EmptyScope()

        scope.span.set_tag(tags.SPAN_KIND, 'operation')

        return scope

    def trace_outbound_request(self, headers, rpc_name=None, parent_ctx=None, skipped=False):
        if not self.enabled:
            return EmptyScope()

        if not rpc_name:
            rpc_name = 'unknown_rpc'
        if parent_ctx:
            rpc_name = '/' + rpc_name
            scope = self.start_active_span(operation_name=rpc_name, child_of=parent_ctx)
        elif self.tracer.active_span or not skipped:
            span = self.tracer.active_span
            path = span.get_baggage_item('path') if span else ''
            rpc_name = path + '/' + rpc_name if path else '/' + rpc_name
            scope = self.start_active_span(operation_name=rpc_name)
        else:
            return EmptyScope()

        scope.span.set_tag(tags.SPAN_KIND, tags.SPAN_KIND_RPC_CLIENT)
        self.inject(scope.span.context, Format.HTTP_HEADERS, headers)

        return scope

    def trace_function_async(self, function_name=None, skipped=True):
        def wrapper(func):
            if not self.enabled:
                return func

            @functools.wraps(func)
            async def wrapped(*args, **kwargs):
                nonlocal function_name
                if function_name is None:
                    function_name = func.__name__ or "unknown_func"
                error = None
                if self._before_function(function_name, skipped):
                    try:
                        r = await func(*args, **kwargs)
                    except Exception as ex:
                        error = ex
                    self._after_function(error=error)
                    if error:
                        raise error
                else:
                    r = await func(*args, **kwargs)
                return r

            return wrapped

        return wrapper
