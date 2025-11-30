# coding=utf-8

from six import reraise as raise_from


def raise_(value, exc=None, *args, **kwargs):
    raise_from(type(value), value, exc and getattr(exc, "__traceback__", None) or None)


# Base class for all exception types raised by the template engine.
class TemplateError(Exception):

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        if hasattr(self, "token") and self.token is not None:
            return "Template '{template_id}', line {line_number}: {msg}".format(template_id=self.token.template_id,
                                                                                line_number=self.token.line_number,
                                                                                msg=self.msg)
        return self.msg


# This exception type may be raised while attempting to load a template file.
class TemplateLoadError(TemplateError):
    pass


# This exception type is raised if the lexer cannot tokenize a template string.
class TemplateLexingError(TemplateError):

    def __init__(self, msg, template_id, line_number):
        super(TemplateLexingError, self).__init__(msg)
        self.template_id = template_id
        self.line_number = line_number

    def __str__(self):
        return "Template '{template_id}', line {line_number}: {msg}".format(template_id=self.template_id,
                                                                                      line_number=self.line_number,
                                                                                      msg=self.msg)


# This exception type may be raised while a template is being compiled.
class TemplateSyntaxError(TemplateError):

    def __init__(self, msg, token):
        super(TemplateSyntaxError, self).__init__(msg)
        self.token = token


# This exception type may be raised while a template is being rendered.
class TemplateRenderingError(TemplateError):

    def __init__(self, msg, token):
        super(TemplateRenderingError, self).__init__(msg)
        self.token = token


# This exception type is raised in strict mode if a variable cannot be resolved.
class UndefinedVariable(TemplateError):

    def __init__(self, msg, token):
        super(UndefinedVariable, self).__init__(msg)
        self.token = token

