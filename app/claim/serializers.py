from rest_framework import serializers
from .models import Expense


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = "__all__"
        extra_kwargs = {
            "employee": {"read_only": True},
            "reviewed_by": {"read_only": True},
            "status": {"read_only": True},
        }


class ApproveExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ["id", "status"]
