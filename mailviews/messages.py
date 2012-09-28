from django.core.exceptions import ImproperlyConfigured
from django.core.mail.message import EmailMessage, EmailMultiAlternatives
from django.template import Context
from django.template.loader import get_template, select_template

from mailviews.utils import unescape


class EmailMessageView(object):
    """
    Base class for encapsulating the logic for the rendering and sending
    class-based email messages.
    """
    message_class = EmailMessage

    def render_subject(self, context):
        raise NotImplementedError  # Must be implemented by subclasses.

    def render_body(self, context):
        raise NotImplementedError  # Must be implemented by subclasses.

    def get_context_data(self, **kwargs):
        """
        Returns the context that will be used for rendering this message.

        :rtype: :class:`django.template.Context`
        """
        return Context(kwargs)

    def render_to_message(self, context, **kwargs):
        """
        Renders and returns a message with the given context without sending it.

        Any extra keyword arguments passed will be passed through as keyword
        arguments to the message constructor.

        :param context: The context to use when rendering templated content.
        :type context: :class:`~django.template.Context`
        :returns: A message instance.
        :rtype: :attr:`.message_class`
        """
        return self.message_class(
            subject=self.render_subject(context),
            body=self.render_body(context),
            **kwargs)

    def send(self, extra_context=None, **kwargs):
        """
        Renders and sends an email message.

        All keyword arguments other than ``context`` are passed through as
        keyword arguments when constructing a new :attr:`message_class`
        instance for this message.

        :param extra_context: Any additional context data that will be used
            when rendering this message.
        :type extra_context: :class:`dict`
        """
        if extra_context is None:
            extra_context = {}

        context = self.get_context_data(**extra_context)
        message = self.render_to_message(context, **kwargs)
        return message.send()


class TemplatedEmailMessageView(EmailMessageView):
    """
    An email message view that uses Django templates for rendering the message
    subject and plain text body.
    """
    #: A template name (or list of template names) that will be used to render
    #: the subject of this message. The rendered subject should be plain text
    #: without any linebreaks. (Any trailing whitespace will be automatically
    #: stripped.) :attr:`.subject_template` will precedence over this value,
    #: if set.
    subject_template_name = None

    #: A template name (or list of template names) that will be used to render
    #: the plain text body of this message. :attr:`.body_template` will take
    #: precedence over this value, if set.
    body_template_name = None

    def _get_template(self, value):
        if isinstance(value, (list, tuple)):
            return select_template(value)
        else:
            return get_template(value)

    def _get_subject_template(self):
        if getattr(self, '_subject_template', None) is not None:
            return self._subject_template

        if self.subject_template_name is None:
            raise ImproperlyConfigured('A subject template name must be provided.')

        return self._get_template(self.subject_template_name)

    def _set_subject_template(self, template):
        self._subject_template = template

    #: Returns the subject template that will be used for rendering this message.
    #: If the subject template has been explicitly set, that template will be
    #: used. If not, the template(s) defined as :attr:`.subject_template_name`
    #: will be used instead.
    subject_template = property(_get_subject_template, _set_subject_template)

    def _get_body_template(self):
        if getattr(self, '_body_template', None) is not None:
            return self._body_template

        if self.body_template_name is None:
            raise ImproperlyConfigured('A body template filename must be provided.')

        return self._get_template(self.body_template_name)

    def _set_body_template(self, template):
        self._body_template = template

    #: Returns the body template that will be used for rendering this message.
    #: If the body template has been explicitly set, that template will be
    #: used. If not, the template(s) defined as :attr:`.body_template_name`
    #: will be used instead.
    body_template = property(_get_body_template, _set_body_template)

    def render_subject(self, context):
        """
        Renders the message subject for the given context.

        The context data is automatically unescaped to avoid rendering HTML
        entities in ``text/plain`` content.

        :param context: The context to use when rendering the subject template.
        :type context: :class:`~django.template.Context`
        :returns: A rendered subject.
        :rtype: :class:`str`
        """
        rendered = self.subject_template.render(unescape(context))
        return rendered.strip()

    def render_body(self, context):
        """
        Renders the message body for the given context.

        The context data is automatically unescaped to avoid rendering HTML
        entities in ``text/plain`` content.

        :param context: The context to use when rendering the body template.
        :type context: :class:`~django.template.Context`
        :returns: A rendered body.
        :rtype: :class:`str`
        """
        return self.body_template.render(unescape(context))


class TemplatedHTMLEmailMessageView(TemplatedEmailMessageView):
    """
    An email message view that uses Django templates for rendering the message
    subject, plain text and HTML body.
    """
    message_class = EmailMultiAlternatives

    #: A template name (or list of template names) that will be used to render
    #: the HTML body of this message. :attr:`.html_body_template` will take
    #: precedence over this value, if set.
    html_body_template_name = None

    def _get_html_body_template(self):
        if getattr(self, '_html_body_template', None) is not None:
            return self._html_body_template

        if self.html_body_template_name is None:
            raise ImproperlyConfigured('A HTML template must be provided.')

        return self._get_template(self.html_body_template_name)

    def _set_html_body_template(self, template):
        self._html_body_template = template

    #: Returns the body template that will be used for rendering the HTML body
    #: of this message. If the HTML body template has been explicitly set, that
    #: template will be used. If not, the template(s) defined as
    #: :attr:`.html_body_template_name` will be used instead.
    html_body_template = property(_get_html_body_template, _set_html_body_template)

    def render_html_body(self, context):
        """
        Renders the message body for the given context.

        :param context: The context to use when rendering the body template.
        :type context: :class:`~django.template.Context`
        :returns: A rendered HTML body.
        :rtype: :class:`str`
        """
        return self.html_body_template.render(context)

    def render_to_message(self, context, *args, **kwargs):
        """
        Renders and returns a message with the given context without sending it.

        Any extra keyword arguments passed will be passed through as keyword
        arguments to the message constructor.

        :param context: The context to use when rendering templated content.
        :type context: :class:`~django.template.Context`
        :returns: A message instance.
        :rtype: :attr:`.message_class`
        """
        message = super(TemplatedHTMLEmailMessageView, self).render_to_message(context, *args, **kwargs)
        message.attach_alternative(content=self.render_html_body(context), mimetype='text/html')
        return message