# Generated for ZIMRA fiscalization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0026_expense_created_by_branch_expense_deleted_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='vatcode',
            name='zimra_tax_id',
            field=models.IntegerField(blank=True, help_text='ZIMRA taxID: 2=Zero%, 3=Exempt, 514=5%, 515=15.5%', null=True),
        ),
        migrations.AddField(
            model_name='paymentmethod',
            name='zimra_money_type_code',
            field=models.IntegerField(default=0, help_text='ZIMRA MoneyType: 0=Cash, 1=Card, 2=MobileWallet, 3=Coupon, 4=Credit, 5=BankTransfer, 6=Other'),
        ),
    ]
