from django.db import models

from apps.accounts.models import CustomUser
from .utils import generate_unique_code


# Create your models here.
class Choice(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    code = models.CharField(max_length=8, unique=True, blank=True)
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='choices')
    winner = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='won_choices'
    )
    award = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    started_at = models.DateField(auto_now_add=True)
    ended_at = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']

    def save(self, *args, **kwargs):
        if not self.code:
            while True:
                code = generate_unique_code()
                if not Choice.objects.filter(code=code).exists():
                    self.code = code
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ChoiceMember(models.Model):
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='choice_memberships')
    joined_at = models.DateTimeField(auto_now_add=True)
    final_score = models.IntegerField(default=0, help_text='Tanlov tugaganida muzlatilgan ball')

    class Meta:
        unique_together = ('choice', 'user')

    def __str__(self):
        return f"{self.user.username} in {self.choice.name}"
