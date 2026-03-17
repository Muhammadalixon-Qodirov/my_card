from django.db import models

from apps.accounts.models import CustomUser


# Create your models here.
class Category(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="categories")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


# modules model
class Module(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="modules")
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="modules")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Module"
        verbose_name_plural = "Modules"
        ordering = ["name"]

    def __str__(self):
        return self.name


# Plan model
class Plan(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    modules = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="plans")
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="plans")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Plan"
        verbose_name_plural = "Plans"
        ordering = ["name"]

    def __str__(self):
        return self.name


# DataCard model
class DataCard(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="data_cards")
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="data_cards")
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="data_cards")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "DataCard"
        verbose_name_plural = "DataCards"
        ordering = ["name"]

    def __str__(self):
        return self.name


# DataCardMedia model
class DataCardMedia(models.Model):
    data_card = models.ForeignKey(DataCard, on_delete=models.CASCADE, related_name="media")
    media_file = models.FileField(upload_to="data_card_media/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "DataCardMedia"
        verbose_name_plural = "DataCardMedia"
        ordering = ["created_at"]

    def __str__(self):
        return f"Media for {self.data_card.name}"



# Modeule Log model
class ModuleLog(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="logs")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="module_logs")
    is_completed = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "ModuleLog"
        verbose_name_plural = "ModuleLogs"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.user.phone} - {'Completed' if self.is_completed else 'Not Completed'} at {self.timestamp}"



# DataCard Log model
class DataCardLog(models.Model):
    data_card = models.ForeignKey(DataCard, on_delete=models.CASCADE, related_name="logs")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="data_card_logs")
    is_completed = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "DataCardLog"
        verbose_name_plural = "DataCardLogs"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.user.phone} - {'Completed' if self.is_completed else 'Not Completed'} at {self.timestamp}"


# Test model
class Test(models.Model):
    question = models.TextField()
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="tests")
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="tests")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Test"
        verbose_name_plural = "Tests"
        ordering = ["created_at"]

    def __str__(self):
        return f"Test for {self.module.name}"


class TestOption(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="options")
    option = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    class Meta:
        verbose_name = "TestOption"
        verbose_name_plural = "TestOptions"
        ordering = ["id"]

    def __str__(self):
        return f"Option for {self.test.question}"


class TestAnswer(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="answers")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="test_answers")
    selected_option = models.ForeignKey(TestOption, on_delete=models.CASCADE, related_name="answers")
    is_correct = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "TestAnswer"
        verbose_name_plural = "TestAnswers"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.user.phone} - Answer for {self.test.question}"
