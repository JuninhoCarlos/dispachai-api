from django.db import models

class Partner(models.Model):
    name = models.CharField(max_length=100)
    type = models.CharField(
        max_length=20,
        choices=[
            ('advogado', 'Advogado'),
            ('corretor', 'Corretor'),
            ('outros', 'Outros'),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type} - {self.name}"