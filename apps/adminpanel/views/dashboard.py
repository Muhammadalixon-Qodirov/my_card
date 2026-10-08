from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import CustomUser
from apps.education.models import (
    Category, DataCard, DataCardLog, Module, ModuleComment, ModuleFeedback,
    ModuleLog, Score, Test, TestAnswer,
)
from apps.news.models import Feedback, News, NewsLog, Question
from apps.society.models import Choice, ChoiceMember
from apps.wallet.models import CoinTransaction
from ..mixins import AdminAPIMixin
from ..querysets import modules_queryset
from ..serializers import AdminUserSerializer, UserBriefSerializer, full_name


def _daily(queryset, field, start):
    rows = (
        queryset.filter(**{f"{field}__date__gte": start})
        .annotate(day=TruncDate(field))
        .values("day")
        .annotate(c=Count("pk"))
        .order_by()
    )
    return {row["day"]: row["c"] for row in rows}


def _active_user_ids(since):
    ids = set()
    for model, field in (
        (TestAnswer, "timestamp"), (DataCardLog, "timestamp"),
        (ModuleLog, "timestamp"), (NewsLog, "created_at"),
    ):
        ids.update(
            model.objects.filter(**{f"{field}__gte": since}).values_list("user_id", flat=True).distinct()
        )
    return ids


class DashboardView(AdminAPIMixin, APIView):
    def get(self, request):
        try:
            days = max(7, min(int(request.query_params.get("days", 30)), 90))
        except ValueError:
            days = 30

        now = timezone.now()
        today = timezone.localdate()
        start = today - timedelta(days=days - 1)
        prev_start = start - timedelta(days=days)

        users = CustomUser.objects.all()
        new_period = users.filter(created_at__date__gte=start).count()
        new_prev = users.filter(created_at__date__gte=prev_start, created_at__date__lt=start).count()

        answers = TestAnswer.objects.aggregate(
            total=Count("id"), correct=Count("id", filter=Q(is_correct=True))
        )
        coins = CoinTransaction.objects.aggregate(
            earned=Sum("amount", filter=Q(transaction_type=CoinTransaction.EARN)),
            spent=Sum("amount", filter=Q(transaction_type=CoinTransaction.SPEND)),
        )
        earned, spent = coins["earned"] or 0, coins["spent"] or 0

        modules = list(modules_queryset())
        feedback_rows = {r["status"]: r["c"] for r in Feedback.objects.values("status").annotate(c=Count("id"))}

        # Kunlik qatorlar
        series_sources = {
            "registrations": _daily(users, "created_at", start),
            "test_answers": _daily(TestAnswer.objects.all(), "timestamp", start),
            "data_cards": _daily(DataCardLog.objects.filter(is_completed=True), "timestamp", start),
            "modules": _daily(Score.objects.all(), "created_at", start),
        }
        series = []
        for offset in range(days):
            day = start + timedelta(days=offset)
            row = {"date": day.isoformat()}
            for key, values in series_sources.items():
                row[key] = values.get(day, 0)
            series.append(row)

        top_modules = sorted(modules, key=lambda m: (m.users_completed, m.users_started), reverse=True)[:8]
        categories = {}
        for module in modules:
            entry = categories.setdefault(
                module.category_id,
                {"id": module.category_id, "name": module.category.name, "modules": 0,
                 "data_cards": 0, "tests": 0, "completions": 0},
            )
            entry["modules"] += 1
            entry["data_cards"] += module.data_cards_count
            entry["tests"] += module.tests_count
            entry["completions"] += module.users_completed

        gender = {r["gender"] or "unknown": r["c"] for r in users.values("gender").annotate(c=Count("id"))}

        return Response({
            "generated_at": now,
            "days": days,
            "users": {
                "total": users.count(),
                "active": users.filter(is_active=True).count(),
                "blocked": users.filter(is_active=False).count(),
                "staff": users.filter(is_staff=True).count(),
                "new_today": users.filter(created_at__date=today).count(),
                "new_7d": users.filter(created_at__date__gte=today - timedelta(days=6)).count(),
                "new_period": new_period,
                "new_prev_period": new_prev,
                "active_24h": len(_active_user_ids(now - timedelta(hours=24))),
                "active_7d": len(_active_user_ids(now - timedelta(days=7))),
                "active_30d": len(_active_user_ids(now - timedelta(days=30))),
                "gender": gender,
            },
            "content": {
                "categories": Category.objects.count(),
                "modules": len(modules),
                "data_cards": DataCard.objects.count(),
                "tests": Test.objects.filter(is_special=False).count(),
                "special_tests": Test.objects.filter(is_special=True).count(),
                "news": News.objects.count(),
                "faq": Question.objects.count(),
                "modules_without_cards": sum(1 for m in modules if m.data_cards_count == 0),
                "modules_without_tests": sum(1 for m in modules if m.tests_count == 0),
                "modules_ready": sum(1 for m in modules if m.data_cards_count and m.tests_count),
            },
            "learning": {
                "module_completions": Score.objects.count(),
                "learners": Score.objects.values("user").distinct().count(),
                "test_answers": answers["total"],
                "correct_answers": answers["correct"],
                "accuracy": round(answers["correct"] * 100 / answers["total"], 1) if answers["total"] else 0,
                "data_cards_completed": DataCardLog.objects.filter(is_completed=True).count(),
                "total_score": Score.objects.aggregate(t=Sum("score"))["t"] or 0,
                "likes": ModuleFeedback.objects.filter(reaction="like").count(),
                "dislikes": ModuleFeedback.objects.filter(reaction="dislike").count(),
            },
            "wallet": {"earned": earned, "spent": spent, "circulation": earned - spent},
            "society": {
                "choices": Choice.objects.count(),
                "active_choices": Choice.objects.filter(is_active=True).count(),
                "members": ChoiceMember.objects.count(),
            },
            "inbox": {
                "feedback_new": feedback_rows.get(Feedback.NEW, 0),
                "feedback_in_progress": feedback_rows.get(Feedback.IN_PROGRESS, 0),
                "feedback_resolved": feedback_rows.get(Feedback.RESOLVED, 0),
                "comments_unanswered": ModuleComment.objects.filter(reply_to__isnull=True)
                .annotate(r=Count("replies")).filter(r=0).count(),
            },
            "series": series,
            "top_modules": [
                {
                    "id": m.id, "name": m.name, "category_name": m.category.name,
                    "users_completed": m.users_completed, "users_started": m.users_started,
                    "likes": m.likes, "dislikes": m.dislikes,
                }
                for m in top_modules
            ],
            "categories": sorted(categories.values(), key=lambda c: c["name"]),
            "recent_users": AdminUserSerializer(
                users.order_by("-created_at")[:6], many=True, context={"request": request}
            ).data,
        })


class ActivityView(AdminAPIMixin, APIView):
    """So'nggi hodisalar tasmasi. ?user=<id> bilan bitta foydalanuvchi bo'yicha."""

    def get(self, request):
        try:
            limit = max(1, min(int(request.query_params.get("limit", 30)), 100))
        except ValueError:
            limit = 30
        user_id = request.query_params.get("user")
        ctx = {"request": request}

        def scoped(qs, field="user"):
            return qs.filter(**{field: user_id}) if user_id else qs

        events = []

        def add(kind, at, user, **data):
            events.append({
                "type": kind, "at": at,
                "user": UserBriefSerializer(user, context=ctx).data, "data": data,
            })

        for u in scoped(CustomUser.objects.all(), "pk").order_by("-created_at")[:limit]:
            add("registered", u.created_at, u, name=full_name(u))
        for s in scoped(Score.objects.select_related("user", "module")).order_by("-created_at")[:limit]:
            add("module_completed", s.created_at, s.user, module=s.module_id,
                module_name=s.module.name, score=s.score, max_score=s.module.score)
        for t in scoped(CoinTransaction.objects.select_related("user")).order_by("-created_at")[:limit]:
            add("coin", t.created_at, t.user, amount=t.amount,
                transaction_type=t.transaction_type, description=t.description)
        for f in scoped(Feedback.objects.select_related("owner"), "owner").order_by("-created_at")[:limit]:
            add("feedback", f.created_at, f.owner, id=f.id, subject=f.subject, feedback_type=f.feedback_type)
        comments = ModuleComment.objects.select_related("user", "module").filter(is_admin_reply=False)
        for c in scoped(comments).order_by("-created_at")[:limit]:
            add("comment", c.created_at, c.user, id=c.id, module=c.module_id,
                module_name=c.module.name, text=c.feedback[:200])
        for r in scoped(ModuleFeedback.objects.select_related("user", "module")).order_by("-created_at")[:limit]:
            add("reaction", r.created_at, r.user, module=r.module_id,
                module_name=r.module.name, reaction=r.reaction)
        for m in scoped(ChoiceMember.objects.select_related("user", "choice")).order_by("-joined_at")[:limit]:
            add("choice_joined", m.joined_at, m.user, choice=m.choice_id, choice_name=m.choice.name)

        events.sort(key=lambda e: e["at"], reverse=True)
        return Response(events[:limit])
