"""Example module forms (server-side validation fallback)."""

from django import forms

from ..models import ExampleItem


class ExampleItemForm(forms.ModelForm):
    """Django form for :class:`~apps.modules.example.models.ExampleItem`.

    Useful for server-rendered pages or as a validation layer in addition to
    the API/service validation.
    """

    class Meta:
        model = ExampleItem
        fields = ["name", "code", "description", "quantity", "sort_order"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
        }

    def clean_code(self):
        code = self.cleaned_data["code"].strip()
        qs = ExampleItem.objects.filter(code=code)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("الكود مستخدم مسبقاً")
        return code
