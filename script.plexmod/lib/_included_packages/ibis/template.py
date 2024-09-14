# coding=utf-8

import ibis
from .context import Context
from .nodes import ExtendsNode, BlockNode


# A Template object is initialized with a template string containing template markup and a
# template ID which is used to identify the template in error messages. The .render() method
# accepts a data dictionary or a set of keyword arguments and returns a rendered output string.
class Template:

    def __init__(self, template_string, template_id="UNIDENTIFIED"):
        self.root_node = ibis.compiler.compile(template_string, template_id)
        self.blocks = self._register_blocks(self.root_node, {})

    def __str__(self):
        return str(self.root_node)

    def render(self, *pargs, **kwargs):
        data_dict = pargs[0] if pargs else kwargs
        strict_mode = kwargs.get("strict_mode", False)
        context = Context(data_dict, strict_mode)
        return self._render(context)

    def _render(self, context):
        context.templates.append(self)
        if self.root_node.children and isinstance(self.root_node.children[0], ExtendsNode):
            if ibis.loader:
                parent_template = ibis.loader(self.root_node.children[0].parent_name)
                return parent_template._render(context)
            else:
                msg = "No template loader has been specified. A template loader is required "
                msg += "by the 'extends' tag in template '{}'.".format(self.template_id)
                raise ibis.errors.TemplateLoadError(msg)
        else:
            return self.root_node.render(context)

    def _register_blocks(self, node, blocks):
        if isinstance(node, BlockNode):
            blocks[node.title] = node
        for child in node.children:
            self._register_blocks(child, blocks)
        return blocks

