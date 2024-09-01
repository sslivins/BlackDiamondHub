import django_tables2 as tables
from .models import Feedback

class FeedbackTable(tables.Table):
    checkbox = tables.CheckBoxColumn(accessor='pk', attrs={"th__input": {"id": "select-all"}})
    icon = tables.TemplateColumn(template_code='''
        {% if record.is_read %}
            <i class="fas fa-envelope-open icon-read"></i>
        {% else %}
            <i class="fas fa-envelope icon-unread"></i>
        {% endif %}
    ''', orderable=False, verbose_name="")
    name = tables.Column(
        verbose_name='From'  # This sets the header for the name column to 'From'
    )
    delete = tables.TemplateColumn(template_code='''
        <i class="fas fa-trash icon-delete" data-feedback-id="{{ record.pk }}"></i>
    ''', orderable=False)
    submitted_at = tables.DateTimeColumn(format='c', accessor='submitted_at', attrs={
        'td': {'class': 'feedback-date'}
    }, verbose_name='Date')

    class Meta:
        model = Feedback
        template_name = "django_tables2/bootstrap4.html"
        fields = ("checkbox", "icon", "name", "submitted_at", "delete")
        attrs = {"class": "table table-hover"}
        sequence = ("checkbox", "icon", "name", "submitted_at", "delete")
        order_by = ('-submitted_at',)
        row_attrs = {
            'data-feedback-id': lambda record: record.pk,
            'data-feedback-date': lambda record: record.submitted_at.isoformat(),
            'data-feedback-name': lambda record: record.name,
            'data-feedback-email': lambda record: record.email,
            'data-feedback-page-url': lambda record: record.page_url,
            'data-feedback-message': lambda record: record.message,
        }
