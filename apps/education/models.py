from django.db import models

from apps.accounts.models import CustomUser


# Create your models here.
class Category(models.Model):
    image = models.ImageField(upload_to="category_images/", blank=True, null=True)
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
    plan = models.TextField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="modules")
    owner = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="modules")
    score = models.IntegerField(default=0)
    coin = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Module"
        verbose_name_plural = "Modules"
        ordering = ["name"]

    def __str__(self):
        return self.name


# DataCard model
class DataCard(models.Model):
    audio = models.FileField(upload_to="data_card_audio/", blank=True, null=True)
    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, null=True)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="data_cards")
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



# Module Log model
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
    is_special = models.BooleanField(default=False)
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


# Module Feedback model
class ModuleFeedback(models.Model):
    REACTION_CHOICES = (
        ('like', "Like"),
        ('dislike', "Dislike"),
    )

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="feedbacks")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="module_feedbacks")
    reaction = models.CharField(max_length=10, choices=REACTION_CHOICES)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ModuleFeedback"
        verbose_name_plural = "ModuleFeedbacks"
        ordering = ["-created_at"]
        unique_together = ("module", "user")

    def __str__(self):
        return f"{self.user.phone} - {self.reaction} on {self.module.name}"


# Score model
class Score(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="scores")
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="scores")
    score = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Score"
        verbose_name_plural = "Scores"
        ordering = ["-updated_at"]
        unique_together = ("user", "module")

    def __str__(self):
        return f"{self.user.phone} - Score for {self.module.name}: {self.score}"


class ModuleQuestion(models.Model):
    text = models.TextField()
    answer = models.TextField()
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="module_questions")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "ModuleQuestion"
        verbose_name_plural = "ModuleQuestions"
        ordering = ["created_at"]

    def __str__(self):
        return f"Question for {self.module.name}"


class ModuleComment(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="module_comments")
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="module_comments")
    feedback = models.TextField()
    reply_to = models.ForeignKey("self", on_delete=models.CASCADE, related_name="replies", blank=True, null=True)
    is_admin_reply = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ModuleComment"
        verbose_name_plural = "ModuleComments"
        ordering = ["-created_at"]

    def __str__(self):
        prefix = "[Admin]" if self.is_admin_reply else "[User]"
        return f"{prefix} {self.user.phone} - Feedback for {self.module.name}"
