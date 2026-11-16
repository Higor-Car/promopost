from django import forms

from .models import Promocao


class PromocaoForm(forms.ModelForm):
    class Meta:
        model = Promocao
        fields = ["comercio", "titulo", "legenda", "imagem", "inicio", "fim"]
        widgets = {
            "inicio": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "fim": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "legenda": forms.Textarea(attrs={"rows": 4}),
        }

    def clean(self):
        dados = super().clean()
        inicio, fim = dados.get("inicio"), dados.get("fim")
        if inicio and fim and fim <= inicio:
            raise forms.ValidationError("O fim da promoção precisa ser depois do início.")
        return dados
