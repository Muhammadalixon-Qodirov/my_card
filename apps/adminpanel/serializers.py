from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from apps.accounts.models import CustomUser, UserDevice
from apps.core.validators import validate_phone_number
from apps.education.models import (
    Category, DataCard, DataCardMedia, Module, ModuleComment, ModuleFeedback,
    ModuleLog, ModuleQuestion, Score, Test, TestAnswer, TestOption,
)
from apps.news.models import Answer, Feedback, News, NewsMedia, Question
from apps.notifications.models import EmergencyNotification, Notification
from apps.society.models import Choice, ChoiceMember
from apps.wallet.models import CoinTransaction


def full_name(user):
    return " ".join(p for p in (user.first_name, user.last_name) if p).strip() or user.phone


# ─── Users ────────────────────────────────────────────────────────────────────
class UserBriefSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ("id", "phone", "first_name", "last_name", "full_name", "profile_image", "is_active")

    def get_full_name(self, obj):
        return full_name(obj)


class AdminUserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    total_score = serializers.IntegerField(read_only=True, default=0)
    coin_balance = serializers.IntegerField(read_only=True, default=0)
    completed_modules = serializers.IntegerField(read_only=True, default=0)
    last_activity = serializers.DateTimeField(read_only=True, default=None)

    class Meta:
        model = CustomUser
        fields = (
            "id", "phone", "first_name", "last_name", "full_name", "gender", "birth_date",
            "profile_image", "is_active", "is_staff", "is_superuser",
            "created_at", "updated_at", "last_login",
            "total_score", "coin_balance", "completed_modules", "last_activity",
        )

    def get_full_name(self, obj):
        return full_name(obj)


class AdminUserWriteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    remove_image = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = CustomUser
        fields = (
            "phone", "first_name", "last_name", "gender", "birth_date", "profile_image",
            "is_active", "is_staff", "is_superuser", "password", "remove_image",
        )
        extra_kwargs = {"profile_image": {"required": False}}

    def validate_phone(self, value):
        try:
            validate_phone_number(value)
        except DjangoValidationError:
            raise serializers.ValidationError("Telefon raqam formati: +998901234567")
        return value

    def validate(self, attrs):
        if not self.instance and not attrs.get("password"):
            raise serializers.ValidationError({"password": "Parol kiritilishi shart."})
        if attrs.get("is_superuser"):
            attrs["is_staff"] = True
        return attrs

    def create(self, validated_data):
        validated_data.pop("remove_image", None)
        password = validated_data.pop("password")
        phone = validated_data.pop("phone")
        return CustomUser.objects.create_user(phone=phone, password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        if validated_data.pop("remove_image", False) and "profile_image" not in validated_data:
            validated_data["profile_image"] = None
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save(update_fields=["password"])
        return instance


class SetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(min_length=8, max_length=128)


class CoinAdjustSerializer(serializers.Serializer):
    amount = serializers.IntegerField(min_value=1, max_value=10_000_000)
    transaction_type = serializers.ChoiceField(choices=[CoinTransaction.EARN, CoinTransaction.SPEND])
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)


class UserDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDevice
        fields = ("id", "device_type", "is_active", "created_at", "updated_at")


# ─── Education ────────────────────────────────────────────────────────────────
class AdminCategorySerializer(serializers.ModelSerializer):
    modules_count = serializers.IntegerField(read_only=True, default=0)
    remove_image = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = Category
        fields = ("id", "name", "description", "image", "created_at", "modules_count", "remove_image")
        read_only_fields = ("id", "created_at")
        extra_kwargs = {"image": {"required": False}}

    def create(self, validated_data):
        validated_data.pop("remove_image", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.pop("remove_image", False) and "image" not in validated_data:
            validated_data["image"] = None
        return super().update(instance, validated_data)


class AdminModuleSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    data_cards_count = serializers.IntegerField(read_only=True, default=0)
    tests_count = serializers.IntegerField(read_only=True, default=0)
    special_tests_count = serializers.IntegerField(read_only=True, default=0)
    questions_count = serializers.IntegerField(read_only=True, default=0)
    comments_count = serializers.IntegerField(read_only=True, default=0)
    users_completed = serializers.IntegerField(read_only=True, default=0)
    users_started = serializers.IntegerField(read_only=True, default=0)
    likes = serializers.IntegerField(read_only=True, default=0)
    dislikes = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Module
        fields = (
            "id", "name", "description", "plan", "category", "category_name", "score", "coin",
            "created_at", "data_cards_count", "tests_count", "special_tests_count",
            "questions_count", "comments_count", "users_completed", "users_started",
            "likes", "dislikes",
        )
        read_only_fields = ("id", "created_at")

    def validate_score(self, value):
        if value < 0:
            raise serializers.ValidationError("Ball manfiy bo'lishi mumkin emas.")
        return value

    def validate_coin(self, value):
        if value < 0:
            raise serializers.ValidationError("Coin manfiy bo'lishi mumkin emas.")
        return value


class AdminDataCardMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataCardMedia
        fields = ("id", "media_file", "created_at")


class AdminDataCardSerializer(serializers.ModelSerializer):
    module_name = serializers.CharField(source="module.name", read_only=True)
    media = AdminDataCardMediaSerializer(many=True, read_only=True)
    media_files = serializers.ListField(child=serializers.FileField(), write_only=True, required=False)
    remove_audio = serializers.BooleanField(write_only=True, required=False, default=False)
    completed_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = DataCard
        fields = (
            "id", "name", "description", "audio", "module", "module_name", "created_at",
            "media", "media_files", "remove_audio", "completed_count",
        )
        read_only_fields = ("id", "created_at")
        extra_kwargs = {"audio": {"required": False}}

    @transaction.atomic
    def create(self, validated_data):
        media_files = validated_data.pop("media_files", [])
        validated_data.pop("remove_audio", None)
        data_card = DataCard.objects.create(**validated_data)
        for media_file in media_files:
            DataCardMedia.objects.create(data_card=data_card, media_file=media_file)
        return data_card

    @transaction.atomic
    def update(self, instance, validated_data):
        media_files = validated_data.pop("media_files", [])
        if validated_data.pop("remove_audio", False) and "audio" not in validated_data:
            validated_data["audio"] = None
        instance = super().update(instance, validated_data)
        for media_file in media_files:
            DataCardMedia.objects.create(data_card=instance, media_file=media_file)
        return instance


class AdminTestOptionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    answers_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = TestOption
        fields = ("id", "option", "is_correct", "answers_count")


class AdminTestSerializer(serializers.ModelSerializer):
    module_name = serializers.CharField(source="module.name", read_only=True)
    options = AdminTestOptionSerializer(many=True)
    answers_count = serializers.IntegerField(read_only=True, default=0)
    correct_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Test
        fields = (
            "id", "question", "module", "module_name", "is_special", "is_active",
            "created_at", "options", "answers_count", "correct_count",
        )
        read_only_fields = ("id", "created_at")

    def validate_options(self, value):
        if len(value) < 2:
            raise serializers.ValidationError("Kamida ikkita variant bo'lishi kerak.")
        if sum(1 for option in value if option.get("is_correct")) != 1:
            raise serializers.ValidationError("Aynan bitta to'g'ri javob belgilanishi kerak.")
        if any(not (option.get("option") or "").strip() for option in value):
            raise serializers.ValidationError("Variant matni bo'sh bo'lmasligi kerak.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        options = validated_data.pop("options")
        test = Test.objects.create(**validated_data)
        TestOption.objects.bulk_create(
            [TestOption(test=test, option=o["option"], is_correct=o["is_correct"]) for o in options]
        )
        return test

    @transaction.atomic
    def update(self, instance, validated_data):
        """Variantlarni id bo'yicha joyida yangilaydi — foydalanuvchi javoblari saqlanib qoladi."""
        options = validated_data.pop("options", None)
        instance = super().update(instance, validated_data)
        if options is None:
            return instance

        existing = {o.id: o for o in instance.options.all()}
        keep_ids = set()
        for data in options:
            option = existing.get(data.get("id"))
            if option:
                changed_correct = option.is_correct != data["is_correct"]
                option.option = data["option"]
                option.is_correct = data["is_correct"]
                option.save(update_fields=["option", "is_correct"])
                if changed_correct:
                    TestAnswer.objects.filter(selected_option=option).update(is_correct=option.is_correct)
                keep_ids.add(option.id)
            else:
                created = TestOption.objects.create(
                    test=instance, option=data["option"], is_correct=data["is_correct"]
                )
                keep_ids.add(created.id)
        instance.options.exclude(id__in=keep_ids).delete()
        return instance


class AdminModuleQuestionSerializer(serializers.ModelSerializer):
    module_name = serializers.CharField(source="module.name", read_only=True)

    class Meta:
        model = ModuleQuestion
        fields = ("id", "text", "answer", "module", "module_name", "created_at")
        read_only_fields = ("id", "created_at")


class AdminCommentReplySerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)

    class Meta:
        model = ModuleComment
        fields = ("id", "user", "feedback", "is_admin_reply", "created_at", "updated_at")


class AdminModuleCommentSerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)
    module_name = serializers.CharField(source="module.name", read_only=True)
    replies = AdminCommentReplySerializer(many=True, read_only=True)

    class Meta:
        model = ModuleComment
        fields = (
            "id", "user", "module", "module_name", "feedback", "reply_to",
            "is_admin_reply", "replies", "created_at", "updated_at",
        )
        read_only_fields = ("id", "user", "module", "reply_to", "is_admin_reply", "created_at", "updated_at")


class ReplySerializer(serializers.Serializer):
    feedback = serializers.CharField(max_length=5000)


class AdminModuleFeedbackSerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)
    module_name = serializers.CharField(source="module.name", read_only=True)

    class Meta:
        model = ModuleFeedback
        fields = ("id", "user", "module", "module_name", "reaction", "comment", "created_at", "updated_at")


class AdminScoreSerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)
    module_name = serializers.CharField(source="module.name", read_only=True)
    max_score = serializers.IntegerField(source="module.score", read_only=True)

    class Meta:
        model = Score
        fields = ("id", "user", "module", "module_name", "score", "max_score", "created_at")


class AdminTestAnswerSerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)
    question = serializers.CharField(source="test.question", read_only=True)
    module = serializers.IntegerField(source="test.module_id", read_only=True)
    module_name = serializers.CharField(source="test.module.name", read_only=True)
    is_special = serializers.BooleanField(source="test.is_special", read_only=True)
    selected_option_text = serializers.CharField(source="selected_option.option", read_only=True)

    class Meta:
        model = TestAnswer
        fields = (
            "id", "user", "test", "question", "module", "module_name", "is_special",
            "selected_option", "selected_option_text", "is_correct", "timestamp",
        )


class AdminModuleLogSerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)
    module_name = serializers.CharField(source="module.name", read_only=True)

    class Meta:
        model = ModuleLog
        fields = ("id", "user", "module", "module_name", "is_completed", "timestamp")


# ─── News / FAQ / Feedback ────────────────────────────────────────────────────
class AdminNewsMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsMedia
        fields = ("id", "media_file", "media_type", "created_at")


class AdminNewsSerializer(serializers.ModelSerializer):
    media = AdminNewsMediaSerializer(many=True, read_only=True)
    media_files = serializers.ListField(child=serializers.FileField(), write_only=True, required=False)
    views_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = News
        fields = ("id", "title", "content", "created_at", "media", "media_files", "views_count")
        read_only_fields = ("id", "created_at")

    def validate_media_files(self, files):
        for f in files:
            if _news_media_type(f) is None:
                raise serializers.ValidationError(f"'{f.name}': faqat rasm yoki video yuklash mumkin.")
        return files

    def _save_media(self, news, files):
        NewsMedia.objects.bulk_create(
            [NewsMedia(news=news, media_file=f, media_type=_news_media_type(f)) for f in files]
        )

    @transaction.atomic
    def create(self, validated_data):
        files = validated_data.pop("media_files", [])
        news = News.objects.create(**validated_data)
        self._save_media(news, files)
        return news

    @transaction.atomic
    def update(self, instance, validated_data):
        files = validated_data.pop("media_files", [])
        instance = super().update(instance, validated_data)
        self._save_media(instance, files)
        return instance


VIDEO_EXTENSIONS = ("mp4", "mov", "avi", "webm", "mkv", "m4v")
IMAGE_EXTENSIONS = ("jpg", "jpeg", "png", "gif", "webp")


def _news_media_type(uploaded):
    content_type = (getattr(uploaded, "content_type", "") or "").lower()
    ext = uploaded.name.rsplit(".", 1)[-1].lower() if "." in uploaded.name else ""
    if content_type.startswith("image/") or ext in IMAGE_EXTENSIONS:
        return "image"
    if content_type.startswith("video/") or ext in VIDEO_EXTENSIONS:
        return "video"
    return None


class AdminFAQSerializer(serializers.ModelSerializer):
    likes_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Question
        fields = ("id", "question", "answer", "likes_count", "created_at")
        read_only_fields = ("id", "created_at")
        ref_name = "AdminFAQ"


class AdminAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = ("id", "answer", "created_at")


class AdminFeedbackSerializer(serializers.ModelSerializer):
    owner = UserBriefSerializer(read_only=True)
    answers = AdminAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = Feedback
        fields = (
            "id", "feedback_type", "subject", "message", "status", "owner",
            "answers", "created_at", "updated_at",
        )
        read_only_fields = ("id", "feedback_type", "subject", "message", "owner", "created_at", "updated_at")


class FeedbackAnswerSerializer(serializers.Serializer):
    answer = serializers.CharField(max_length=5000)
    status = serializers.ChoiceField(
        choices=[Feedback.NEW, Feedback.IN_PROGRESS, Feedback.RESOLVED], required=False
    )


# ─── Notifications ────────────────────────────────────────────────────────────
class AdminEmergencySerializer(serializers.ModelSerializer):
    remove_image = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = EmergencyNotification
        fields = ("id", "title", "body", "image", "is_active", "created_at", "remove_image")
        read_only_fields = ("id", "created_at")
        extra_kwargs = {"image": {"required": False}}

    def create(self, validated_data):
        validated_data.pop("remove_image", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.pop("remove_image", False) and "image" not in validated_data:
            validated_data["image"] = None
        return super().update(instance, validated_data)


class AdminNotificationSerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = ("id", "user", "title", "body", "notification_type", "extra_data", "is_read", "created_at")


class BroadcastSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    body = serializers.CharField(max_length=4000)
    audience = serializers.ChoiceField(choices=["all", "users"], default="all")
    user_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, allow_empty=True, max_length=5000
    )

    def validate(self, attrs):
        if attrs["audience"] == "users" and not attrs.get("user_ids"):
            raise serializers.ValidationError({"user_ids": "Kamida bitta foydalanuvchi tanlang."})
        return attrs


# ─── Wallet / Society ─────────────────────────────────────────────────────────
class AdminTransactionSerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)
    module_name = serializers.CharField(source="module.name", read_only=True, default=None)

    class Meta:
        model = CoinTransaction
        fields = ("id", "user", "amount", "transaction_type", "description", "module", "module_name", "created_at")


class AdminChoiceSerializer(serializers.ModelSerializer):
    owner = UserBriefSerializer(read_only=True)
    winner = UserBriefSerializer(read_only=True)
    member_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Choice
        fields = (
            "id", "name", "description", "code", "is_public", "owner", "winner", "award",
            "is_active", "started_at", "ended_at", "member_count",
        )
        read_only_fields = ("id", "code", "is_public", "owner", "winner", "award", "is_active", "started_at")


class AdminChoiceMemberSerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)

    class Meta:
        model = ChoiceMember
        fields = ("id", "user", "joined_at", "final_score")
