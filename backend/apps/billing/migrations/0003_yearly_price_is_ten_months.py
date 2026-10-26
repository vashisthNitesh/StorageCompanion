from decimal import Decimal

from django.db import migrations, models

YEARLY_PAID_MONTHS = 10


def sync_yearly_prices(apps, schema_editor):
    """Yearly = monthly x 10 for every plan. Orders and invoices keep the amounts they were charged."""
    Plan = apps.get_model("billing", "Plan")
    for plan in Plan.objects.all():
        yearly = Decimal(plan.price_monthly) * YEARLY_PAID_MONTHS
        if plan.price_yearly != yearly:
            plan.price_yearly = yearly
            plan.save(update_fields=["price_yearly"])


class Migration(migrations.Migration):
    dependencies = [("billing", "0002_invoice_billing_interval_invoice_place_of_supply_and_more")]

    operations = [
        migrations.AlterField(
            model_name="plan",
            name="price_yearly",
            field=models.DecimalField(decimal_places=2, default=0, editable=False, max_digits=10),
        ),
        migrations.RunPython(sync_yearly_prices, migrations.RunPython.noop),
    ]
