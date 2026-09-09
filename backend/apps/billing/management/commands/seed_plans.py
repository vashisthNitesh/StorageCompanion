from django.core.management.base import BaseCommand
from apps.billing.models import Plan


class Command(BaseCommand):
    help = "Seed SmartSpace Data 5 subscription plans (Entry, Smart, Value, Super, Mega). No dummy users or dummy files."

    def handle(self, *args, **options):
        self.stdout.write("Seeding SmartSpace Data subscription plans...")

        # 1. Entry Pack (25 GB - ₹39/mo)
        Plan.objects.update_or_create(
            code="entry",
            defaults={
                "name": "Entry Pack",
                "description": "Essential cloud vault for documents, tax receipts, and personal archives.",
                "storage_bytes": 25 * 1024 * 1024 * 1024,  # 25 GB
                "price_monthly": 39.00,
                "price_yearly": 390.00,
                "currency": "INR",
                "max_file_size": 5 * 1024 * 1024 * 1024,  # 5 GB
                "version_retention_days": 15,
                "sort_order": 1,
                "is_active": True,
                "features": [
                    "25 GB Encrypted Storage",
                    "100% Original RAW Quality",
                    "Zero Egress Bandwidth Fees",
                    "Client-Side Zero-Knowledge Encryption",
                    "1-Click UPI via Razorpay",
                ],
            },
        )

        # 2. Smart Pack (100 GB - ₹89/mo)
        Plan.objects.update_or_create(
            code="smart",
            defaults={
                "name": "Smart Pack",
                "description": "Affordable expansion for students, creators, and personal photo libraries.",
                "storage_bytes": 100 * 1024 * 1024 * 1024,  # 100 GB
                "price_monthly": 89.00,
                "price_yearly": 890.00,
                "currency": "INR",
                "max_file_size": 10 * 1024 * 1024 * 1024,  # 10 GB
                "version_retention_days": 30,
                "sort_order": 2,
                "is_active": True,
                "features": [
                    "100 GB Encrypted Storage",
                    "100% Original RAW Quality",
                    "Zero Egress Bandwidth Fees",
                    "Client-Side Decrypted Search",
                    "Password-Protected Share Links",
                ],
            },
        )

        # 3. Value Pack (200 GB - ₹149/mo)
        Plan.objects.update_or_create(
            code="value",
            defaults={
                "name": "Value Pack",
                "description": "Top-tier value for photographers, wedding cinematographers, and 4K archives.",
                "storage_bytes": 200 * 1024 * 1024 * 1024,  # 200 GB
                "price_monthly": 149.00,
                "price_yearly": 1490.00,
                "currency": "INR",
                "max_file_size": 25 * 1024 * 1024 * 1024,  # 25 GB
                "version_retention_days": 60,
                "sort_order": 3,
                "is_active": True,
                "features": [
                    "200 GB Encrypted Storage",
                    "Hero Pack - Most Popular",
                    "100% Original RAW Quality",
                    "Zero Bandwidth Limits",
                    "Cryptographic File Integrity Verification",
                    "Fastest Direct S3 Presigned Uploads",
                ],
            },
        )

        # 4. Super Pack (400 GB - ₹249/mo)
        Plan.objects.update_or_create(
            code="super",
            defaults={
                "name": "Super Pack",
                "description": "High-volume secure storage for video editors, boutique studios, and agencies.",
                "storage_bytes": 400 * 1024 * 1024 * 1024,  # 400 GB
                "price_monthly": 249.00,
                "price_yearly": 2490.00,
                "currency": "INR",
                "max_file_size": 50 * 1024 * 1024 * 1024,  # 50 GB
                "version_retention_days": 90,
                "sort_order": 4,
                "is_active": True,
                "features": [
                    "400 GB Encrypted Storage",
                    "Extended 90-Day File Version History",
                    "Granular Share Permissions & Expiry Dates",
                    "High-Throughput Parallel Uploads",
                    "Priority Direct WhatsApp & Email Support",
                ],
            },
        )

        # 5. Mega Pack (1 TB - ₹449/mo)
        Plan.objects.update_or_create(
            code="mega",
            defaults={
                "name": "Mega Pack",
                "description": "Maximum capacity tier for enterprise datasets and production media houses.",
                "storage_bytes": 1000 * 1024 * 1024 * 1024,  # 1 TB (1000 GB)
                "price_monthly": 449.00,
                "price_yearly": 4490.00,
                "currency": "INR",
                "max_file_size": 100 * 1024 * 1024 * 1024,  # 100 GB
                "version_retention_days": 365,
                "sort_order": 5,
                "is_active": True,
                "features": [
                    "1,000 GB (1 TB) Massive Vault Storage",
                    "Full 365-Day Versioning Retention",
                    "Client-Side Zero-Knowledge Cryptography",
                    "24/7 Dedicated Account Manager",
                    "Custom Domain Sharing Capabilities",
                ],
            },
        )

        # Deactivate legacy placeholder plans
        Plan.objects.filter(code__in=["personal", "business"]).update(is_active=False)

        self.stdout.write(
            self.style.SUCCESS("✓ All 5 SmartSpace Data plans successfully seeded (no dummy accounts created).")
        )
