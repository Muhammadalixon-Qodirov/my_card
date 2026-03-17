from rest_framework import serializers

from .models import (
    Category,
    Module,
    Plan,
    DataCard,
    DataCardMedia,
    ModuleLog,
    DataCardLog,
    Test,
    TestOption,
    TestAnswer,
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "description", "owner", "created_at")
        read_only_fields = ("id", "owner", "created_at")


class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ("id", "name", "description", "category", "owner", "created_at")
        read_only_fields = ("id", "owner", "created_at")


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ("id", "name", "description", "modules", "owner", "created_at")
        read_only_fields = ("id", "owner", "created_at")


class DataCardMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataCardMedia
        fields = ("id", "media_file", "created_at")
        read_only_fields = ("id", "created_at")


class DataCardSerializer(serializers.ModelSerializer):
    media = DataCardMediaSerializer(many=True, read_only=True)
    media_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
    )

    class Meta:
        model = DataCard
        fields = (
            "id",
            "name",
            "description",
            "module",
            "plan",
            "owner",
            "created_at",
            "media",
            "media_files",
        )
        read_only_fields = ("id", "owner", "created_at", "media")

    def validate(self, attrs):
        module = attrs.get("module")
        plan = attrs.get("plan")

        if self.instance:
            module = module or self.instance.module
            plan = plan or self.instance.plan

        if module and plan and plan.modules_id != module.id:
            raise serializers.ValidationError("Plan tanlangan modulga tegishli bo'lishi kerak.")

        return attrs

    def create(self, validated_data):
        media_files = validated_data.pop("media_files", [])
        data_card = DataCard.objects.create(**validated_data)

        for media_file in media_files:
            DataCardMedia.objects.create(data_card=data_card, media_file=media_file)

        return data_card

    def update(self, instance, validated_data):
        media_files = validated_data.pop("media_files", None)
        instance = super().update(instance, validated_data)

        if media_files:
            for media_file in media_files:
                DataCardMedia.objects.create(data_card=instance, media_file=media_file)

        return instance


class ModuleLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModuleLog
        fields = ("id", "module", "user", "is_completed", "timestamp")
        read_only_fields = ("id", "user", "timestamp")


class DataCardLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataCardLog
        fields = ("id", "data_card", "user", "is_completed", "timestamp")
        read_only_fields = ("id", "user", "timestamp")


class TestOptionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = TestOption
        fields = ("id", "option", "is_correct")


class TestSerializer(serializers.ModelSerializer):
    options = TestOptionSerializer(many=True)

    class Meta:
        model = Test
        fields = ("id", "question", "module", "owner", "is_active", "created_at", "options")
        read_only_fields = ("id", "owner", "created_at")

    def validate_options(self, value):
        if not value:
            raise serializers.ValidationError("Kamida bitta variant bo'lishi kerak.")

        correct_count = sum(1 for option in value if option.get("is_correct"))
        if correct_count != 1:
            raise serializers.ValidationError("Har bir testda faqat bitta to'g'ri javob bo'lishi kerak.")
        return value

    def create(self, validated_data):
        options_data = validated_data.pop("options", [])
        test = Test.objects.create(**validated_data)

        for option_data in options_data:
            TestOption.objects.create(test=test, **option_data)

        return test

    def update(self, instance, validated_data):
        options_data = validated_data.pop("options", None)
        instance = super().update(instance, validated_data)

        if options_data is not None:
            instance.options.all().delete()
            for option_data in options_data:
                option_data.pop("id", None)
                TestOption.objects.create(test=instance, **option_data)

        return instance


class TestAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestAnswer
        fields = ("id", "test", "user", "selected_option", "is_correct", "timestamp")
        read_only_fields = ("id", "user", "is_correct", "timestamp")

    def validate(self, attrs):
        test = attrs.get("test")
        selected_option = attrs.get("selected_option")
        request = self.context.get("request")

        if self.instance:
            test = test or self.instance.test
            selected_option = selected_option or self.instance.selected_option

        if selected_option and test and selected_option.test_id != test.id:
            raise serializers.ValidationError("Tanlangan variant ushbu testga tegishli emas.")

        if test and not test.is_active:
            raise serializers.ValidationError("Ushbu test faol emas.")

        if request and request.user and request.user.is_authenticated and test:
            module_data_cards_count = test.module.data_cards.count()
            if module_data_cards_count > 0:
                completed_count = DataCardLog.objects.filter(
                    user=request.user,
                    data_card__module=test.module,
                    is_completed=True,
                ).values("data_card_id").distinct().count()

                if completed_count < module_data_cards_count:
                    raise serializers.ValidationError(
                        "Test ishlashdan oldin moduldagi barcha datacardlarni tugatish kerak."
                    )

        return attrs

    def create(self, validated_data):
        validated_data["is_correct"] = validated_data["selected_option"].is_correct
        return super().create(validated_data)

    def update(self, instance, validated_data):
        selected_option = validated_data.get("selected_option", instance.selected_option)
        validated_data["is_correct"] = selected_option.is_correct
        return super().update(instance, validated_data)
