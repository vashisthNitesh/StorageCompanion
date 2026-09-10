import uuid
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.db import models
from django.db.models import Count, Sum
from django.db.models.functions import TruncHour, TruncDay, TruncMonth
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.accounts.models import User
from apps.billing.models import Plan, Subscription, Invoice
from apps.storage.models import StorageQuota, Node, FileVersion
from apps.audit.models import AuditLog


class AdminKPIsView(APIView):
    """
    Returns time-filtered Key Performance Indicators for the Master Admin:
    - Daily, Weekly, Monthly, and Yearly activity
    - Active users, new users, total storage consumed
    - Plan distribution (which plan is most used)
    - Activity trend time-series
    - Recent audit log feed
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get(self, request):
        period = request.query_params.get("period", "weekly").lower()
        now = timezone.now()

        if period == "daily":
            start_date = now - timedelta(days=1)
            bucket_format = "%H:00"
            bucket_count = 24
        elif period == "weekly":
            start_date = now - timedelta(days=7)
            bucket_format = "%a"
            bucket_count = 7
        elif period == "yearly":
            start_date = now - timedelta(days=365)
            bucket_format = "%b"
            bucket_count = 12
        else:  # monthly default
            period = "monthly"
            start_date = now - timedelta(days=30)
            bucket_format = "%d %b"
            bucket_count = 30

        # 1. Customer User Metrics (Exclude Master Admin & Staff)
        customer_users_qs = User.objects.filter(is_staff=False, is_superuser=False)
        total_users = customer_users_qs.count()
        new_users = customer_users_qs.filter(date_joined__gte=start_date).count()

        # Active customer users in period (distinct non-staff users with audit logs or who joined recently)
        active_user_ids = set(
            AuditLog.objects.filter(
                created_at__gte=start_date,
                user__isnull=False,
                user__is_staff=False,
                user__is_superuser=False,
            )
            .values_list("user_id", flat=True)
            .distinct()
        )
        recent_join_ids = set(
            customer_users_qs.filter(date_joined__gte=start_date).values_list("id", flat=True)
        )
        active_users_count = len(active_user_ids | recent_join_ids)

        # 2. Global Storage Pool Metrics
        pool_stats = StorageQuota.get_global_pool_stats()

        # 3. Revenue Estimation (calculated strictly from customer subscriptions)
        active_subs = Subscription.objects.filter(
            status="active",
            user__is_staff=False,
            user__is_superuser=False,
        ).select_related("plan")
        monthly_revenue = Decimal("0.00")
        for sub in active_subs:
            if sub.plan:
                if sub.billing_interval == "yearly":
                    monthly_revenue += (sub.plan.price_yearly / 12)
                else:
                    monthly_revenue += sub.plan.price_monthly

        # 4. Plan Distribution (Customer plans only)
        all_plans = list(Plan.objects.filter(is_active=True).order_by("sort_order"))
        plan_counts = {p.code: 0 for p in all_plans}
        plan_names = {p.code: p.name for p in all_plans}
        
        subs_distribution = (
            Subscription.objects.filter(
                status="active",
                user__is_staff=False,
                user__is_superuser=False,
            )
            .values("plan__code")
            .annotate(count=Count("id"))
        )
        for item in subs_distribution:
            code = item["plan__code"]
            if code in plan_counts:
                plan_counts[code] = item["count"]

        total_active_subs = sum(plan_counts.values()) or 1
        plan_distribution = []
        for p in all_plans:
            count = plan_counts.get(p.code, 0)
            percent = round((count / total_active_subs) * 100, 1)
            plan_distribution.append({
                "code": p.code,
                "name": p.name,
                "count": count,
                "percent": percent,
                "storage_gb": round(p.storage_bytes / (1024 * 1024 * 1024)),
                "price_monthly": float(p.price_monthly),
                "price_yearly": float(p.price_yearly),
            })

        # Sort by count desc to highlight most popular
        active_plans = [p for p in plan_distribution if p["count"] > 0]
        most_popular_plan = max(active_plans, key=lambda x: x["count"]) if active_plans else None

        # 5. Activity Time-Series Breakdown
        trend_points = []
        if period == "daily":
            for h in range(24):
                slot_time = now - timedelta(hours=23 - h)
                slot_start = slot_time.replace(minute=0, second=0, microsecond=0)
                slot_end = slot_start + timedelta(hours=1)
                logins = AuditLog.objects.filter(action__icontains="login", created_at__gte=slot_start, created_at__lt=slot_end).count()
                uploads = AuditLog.objects.filter(action__icontains="upload", created_at__gte=slot_start, created_at__lt=slot_end).count()
                shares = AuditLog.objects.filter(action__icontains="share", created_at__gte=slot_start, created_at__lt=slot_end).count()
                trend_points.append({
                    "label": slot_start.strftime("%H:00"),
                    "uploads": uploads,
                    "logins": logins,
                    "shares": shares,
                    "total": uploads + logins + shares,
                })
        elif period == "weekly":
            for d in range(7):
                slot_time = now - timedelta(days=6 - d)
                slot_start = slot_time.replace(hour=0, minute=0, second=0, microsecond=0)
                slot_end = slot_start + timedelta(days=1)
                logins = AuditLog.objects.filter(action__icontains="login", created_at__gte=slot_start, created_at__lt=slot_end).count()
                uploads = AuditLog.objects.filter(action__icontains="upload", created_at__gte=slot_start, created_at__lt=slot_end).count()
                shares = AuditLog.objects.filter(action__icontains="share", created_at__gte=slot_start, created_at__lt=slot_end).count()
                trend_points.append({
                    "label": slot_start.strftime("%a"),
                    "uploads": uploads,
                    "logins": logins,
                    "shares": shares,
                    "total": uploads + logins + shares,
                })
        elif period == "monthly":
            for d in range(30):
                slot_time = now - timedelta(days=29 - d)
                slot_start = slot_time.replace(hour=0, minute=0, second=0, microsecond=0)
                slot_end = slot_start + timedelta(days=1)
                logins = AuditLog.objects.filter(action__icontains="login", created_at__gte=slot_start, created_at__lt=slot_end).count()
                uploads = AuditLog.objects.filter(action__icontains="upload", created_at__gte=slot_start, created_at__lt=slot_end).count()
                shares = AuditLog.objects.filter(action__icontains="share", created_at__gte=slot_start, created_at__lt=slot_end).count()
                trend_points.append({
                    "label": slot_start.strftime("%d %b"),
                    "uploads": uploads,
                    "logins": logins,
                    "shares": shares,
                    "total": uploads + logins + shares,
                })
        elif period == "yearly":
            for m in range(12):
                month_date = (now.replace(day=1) - timedelta(days=(11 - m) * 30)).replace(day=1)
                slot_start = month_date.replace(hour=0, minute=0, second=0, microsecond=0)
                # Next month approximation
                if slot_start.month == 12:
                    slot_end = slot_start.replace(year=slot_start.year + 1, month=1)
                else:
                    slot_end = slot_start.replace(month=slot_start.month + 1)
                logins = AuditLog.objects.filter(action__icontains="login", created_at__gte=slot_start, created_at__lt=slot_end).count()
                uploads = AuditLog.objects.filter(action__icontains="upload", created_at__gte=slot_start, created_at__lt=slot_end).count()
                shares = AuditLog.objects.filter(action__icontains="share", created_at__gte=slot_start, created_at__lt=slot_end).count()
                trend_points.append({
                    "label": slot_start.strftime("%b %Y"),
                    "uploads": uploads,
                    "logins": logins,
                    "shares": shares,
                    "total": uploads + logins + shares,
                })

        # 6. Recent Audit Activity Stream
        recent_logs = []
        for log in AuditLog.objects.select_related("user").order_by("-created_at")[:15]:
            recent_logs.append({
                "id": str(log.id),
                "action": log.action,
                "user_email": log.user.email if log.user else "Anonymous",
                "ip": log.ip,
                "created_at": log.created_at.isoformat(),
            })

        # 7. Total Vault Nodes
        total_files = Node.objects.filter(type="file", trashed_at__isnull=True).count()
        total_folders = Node.objects.filter(type="folder", trashed_at__isnull=True).count()

        return Response({
            "period": period,
            "kpis": {
                "total_users": total_users,
                "new_users": new_users,
                "active_users": active_users_count,
                "total_files": total_files,
                "total_folders": total_folders,
                "monthly_recurring_revenue": float(round(monthly_revenue, 2)),
                "pool_used_gb": pool_stats["used_gb"],
                "pool_total_gb": pool_stats["total_pool_gb"],
                "pool_percent_used": pool_stats["percent_used"],
                "most_popular_plan": most_popular_plan["name"] if most_popular_plan else "None Yet",
            },
            "plan_distribution": plan_distribution,
            "activity_trend": trend_points,
            "recent_activity": recent_logs,
        })


class AdminPoolStatusView(APIView):
    """
    Returns SpaceByte Upstream Pool Status and capacity planning details.
    Allows the Master Admin to inspect pool utilization and evaluate expansion options.
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get(self, request):
        stats = StorageQuota.get_global_pool_stats()
        from apps.storage.spacebyte import get_spacebyte_client
        sb_client = get_spacebyte_client()

        percent = stats["percent_used"]
        committed_percent = stats.get("committed_percent", 0.0)

        # Evaluate health based on both physical disk consumption and sold quota commitment
        if percent >= 90 or committed_percent >= 100:
            pool_health = "critical"
            if percent >= 90:
                health_message = "Storage pool is over 90% physical capacity! Urgent upstream expansion required."
            else:
                health_message = f"Pool is fully committed to subscribers ({stats.get('committed_gb', 0)} GB). Upstream expansion required for new subscriptions."
        elif percent >= 75 or committed_percent >= 80:
            pool_health = "warning"
            if percent >= 75:
                health_message = "Storage pool is approaching 75% physical capacity. Consider purchasing additional capacity."
            else:
                health_message = f"Storage pool committed quota is at {committed_percent}%. Consider purchasing additional capacity."
        else:
            pool_health = "optimal"
            health_message = "Upstream SpaceByte pool operating smoothly within safe testing parameters."

        max_load = max(percent, committed_percent)
        expansion_tiers = [
            {"label": "+1 TB Upstream Expansion", "size_gb": 1000, "estimated_price": "₹4,490/yr", "recommended": max_load > 70},
            {"label": "+5 TB Studio Cluster Expansion", "size_gb": 5000, "estimated_price": "₹19,990/yr", "recommended": max_load > 85},
            {"label": "+10 TB Enterprise Scale Expansion", "size_gb": 10000, "estimated_price": "₹34,990/yr", "recommended": False},
        ]

        return Response({
            **stats,
            "is_connected": sb_client.is_configured,
            "base_url": sb_client.base_url,
            "pool_health": pool_health,
            "health_message": health_message,
            "expansion_tiers": expansion_tiers,
        })


class AdminUsersListView(APIView):
    """
    Searchable, paginated user management table for Master Admin.
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get(self, request):
        search = request.query_params.get("search", "").strip().lower()
        plan_filter = request.query_params.get("plan", "").strip().lower()
        status_filter = request.query_params.get("status", "").strip().lower()

        # Strictly customer accounts: exclude Platform Administrator & staff
        queryset = (
            User.objects.filter(is_staff=False, is_superuser=False)
            .select_related("subscription__plan", "storage_quota")
            .order_by("-date_joined")
        )

        if search:
            queryset = queryset.filter(
                models.Q(email__icontains=search) | models.Q(full_name__icontains=search)
            )

        if plan_filter:
            queryset = queryset.filter(subscription__plan__code=plan_filter)

        if status_filter == "active":
            queryset = queryset.filter(is_active=True)
        elif status_filter == "suspended":
            queryset = queryset.filter(is_active=False)

        total_count = queryset.count()

        # Simple pagination
        try:
            page = max(1, int(request.query_params.get("page", 1)))
            page_size = min(100, max(1, int(request.query_params.get("page_size", 20))))
        except ValueError:
            page = 1
            page_size = 20

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paged_users = queryset[start_idx:end_idx]

        results = []
        for user in paged_users:
            sub = getattr(user, "subscription", None)
            quota = getattr(user, "storage_quota", None)

            bytes_used = quota.bytes_used if quota else 0
            bytes_limit = quota.bytes_limit if quota else (sub.plan.storage_bytes if sub and sub.plan else 0)
            percent_used = round((bytes_used / bytes_limit * 100), 1) if bytes_limit > 0 else 0.0

            results.append({
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name or user.email.split("@")[0],
                "is_staff": False,
                "is_superuser": False,
                "is_active": user.is_active,
                "date_joined": user.date_joined.isoformat(),
                "plan": {
                    "code": sub.plan.code if sub and sub.plan else "none",
                    "name": sub.plan.name if sub and sub.plan else "No Active Plan",
                    "status": sub.status if sub else "inactive",
                    "billing_interval": sub.billing_interval if sub else "monthly",
                    "current_period_end": sub.current_period_end.isoformat() if sub and sub.current_period_end else None,
                },
                "storage": {
                    "bytes_used": bytes_used,
                    "bytes_limit": bytes_limit,
                    "percent_used": percent_used,
                    "used_formatted": f"{round(bytes_used / (1024 * 1024), 1)} MB" if bytes_used < 1024 * 1024 * 1024 else f"{round(bytes_used / (1024 * 1024 * 1024), 2)} GB",
                    "limit_formatted": f"{round(bytes_limit / (1024 * 1024 * 1024), 1)} GB",
                },
            })

        return Response({
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "results": results,
        })


class AdminUserPlanUpgradeView(APIView):
    """
    Allows Master Admin to upgrade, downgrade, or assign any plan or custom storage quota to a user.
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def post(self, request, user_id):
        target_user = get_object_or_404(User, id=user_id)
        if target_user.is_staff or target_user.is_superuser:
            return Response(
                {"error": "Super Admin is the platform administrator and does not hold a customer storage pack."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plan_code = request.data.get("plan_code", "").strip().lower()
        billing_interval = request.data.get("billing_interval", "monthly").strip().lower()
        custom_limit_gb = request.data.get("custom_limit_gb")

        plan = Plan.objects.filter(code=plan_code).first()
        if not plan:
            return Response(
                {"error": f"Invalid plan code '{plan_code}'. Available plans: entry, smart, value, super, mega."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update or create subscription
        duration_days = 365 if billing_interval == "yearly" else 30
        now = timezone.now()
        sub, _ = Subscription.objects.update_or_create(
            user=target_user,
            defaults={
                "plan": plan,
                "status": "active",
                "provider": "admin_granted",
                "billing_interval": billing_interval,
                "current_period_start": now,
                "current_period_end": now + timedelta(days=duration_days),
            },
        )

        # Update storage quota limit
        quota, _ = StorageQuota.objects.get_or_create(user=target_user)
        if custom_limit_gb:
            quota.bytes_limit = int(custom_limit_gb) * 1024 * 1024 * 1024
        else:
            quota.bytes_limit = plan.storage_bytes
        quota.save(update_fields=["bytes_limit"])

        # Audit log
        AuditLog.objects.create(
            user=request.user,
            action="admin.user_plan_upgraded",
            target_type="user",
            target_id=str(target_user.id),
            metadata={
                "target_user_email": target_user.email,
                "new_plan": plan.name,
                "plan_code": plan.code,
                "interval": billing_interval,
                "bytes_limit": quota.bytes_limit,
            },
        )

        return Response({
            "success": True,
            "message": f"Successfully updated {target_user.email}'s plan to {plan.name} ({billing_interval}).",
            "user_id": str(target_user.id),
            "plan_name": plan.name,
            "bytes_limit": quota.bytes_limit,
            "limit_gb": round(quota.bytes_limit / (1024 * 1024 * 1024)),
        })


class AdminUserStatusToggleView(APIView):
    """
    Allows Master Admin to toggle a user's active status (suspend or activate account).
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def post(self, request, user_id):
        target_user = get_object_or_404(User, id=user_id)
        if target_user.id == request.user.id:
            return Response(
                {"error": "Master Admin cannot deactivate their own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target_user.is_active = not target_user.is_active
        target_user.save(update_fields=["is_active"])

        AuditLog.objects.create(
            user=request.user,
            action="admin.user_status_toggled",
            target_type="user",
            target_id=str(target_user.id),
            metadata={
                "target_user_email": target_user.email,
                "is_active": target_user.is_active,
            },
        )

        state_str = "activated" if target_user.is_active else "suspended"
        return Response({
            "success": True,
            "message": f"Account for {target_user.email} has been {state_str}.",
            "is_active": target_user.is_active,
        })
