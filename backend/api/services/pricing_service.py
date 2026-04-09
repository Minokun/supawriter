"""Pricing service for subscription plans and quota packs."""
from typing import Dict, List, Any
from datetime import datetime


class PricingService:
    """
    Service for managing pricing plans and quota packs.

    Provides static pricing configuration for subscriptions and quota packs.
    """

    # Plan configurations
    PLANS = {
        "free": {
            "id": "free",
            "name": "Free",
            "prices": {
                "monthly": 0,
                "quarterly": 0,
                "yearly": 0
            },
            "quota": 5,  # articles per month
            "features": [
                "基础模型",
                "5次/月生成"
            ]
        },
        "pro": {
            "id": "pro",
            "name": "Pro",
            "prices": {
                "monthly": 2990,  # ¥29.90 in cents
                "quarterly": 7990,  # ¥79.90 in cents
                "yearly": 29900  # ¥299.00 in cents
            },
            "quota": 20,  # articles per month
            "popular": True,
            "features": [
                "中级模型",
                "20次/月生成",
                "SEO优化",
                "多平台转换",
                "热点预警",
                "去水印",
                "数据看板（含图表）"
            ]
        },
        "ultra": {
            "id": "ultra",
            "name": "Ultra",
            "prices": {
                "monthly": 5990,  # ¥59.90 in cents
                "quarterly": 14900,  # ¥149.00 in cents
                "yearly": 49900  # ¥499.00 in cents
            },
            "quota": 60,  # articles per month
            "features": [
                "顶级模型",
                "60次/月生成",
                "SEO优化",
                "多平台转换",
                "热点预警",
                "去水印",
                "完整数据看板",
                "批量生成",
                "写作Agent"
            ]
        }
    }

    # Quota pack configurations
    QUOTA_PACKS = {
        "pack_10": {
            "id": "pack_10",
            "name": "10次额度包",
            "quota": 10,
            "price": 1990,  # ¥19.90 in cents
            "validity_days": 365
        },
        "pack_50": {
            "id": "pack_50",
            "name": "50次额度包",
            "quota": 50,
            "price": 7990,  # ¥79.90 in cents
            "validity_days": 365
        }
    }

    @classmethod
    def get_pricing_plans(cls, period: str = "monthly") -> List[Dict[str, Any]]:
        """
        Get all pricing plans for a specific billing period.

        Args:
            period: Billing period ('monthly', 'quarterly', 'yearly')

        Returns:
            List of plan dictionaries
        """
        if period not in ["monthly", "quarterly", "yearly"]:
            period = "monthly"

        plans = []
        for plan_id, plan_config in cls.PLANS.items():
            plan = {
                "id": plan_config["id"],
                "name": plan_config["name"],
                "prices": plan_config["prices"],
                "current_price": plan_config["prices"][period],
                "features": plan_config["features"],
                "quota": plan_config["quota"]
            }
            if "popular" in plan_config:
                plan["popular"] = plan_config["popular"]
            plans.append(plan)

        return plans

    @classmethod
    def get_quota_packs(cls) -> List[Dict[str, Any]]:
        """
        Get all available quota packs.

        Returns:
            List of quota pack dictionaries
        """
        packs = []
        for pack_id, pack_config in cls.QUOTA_PACKS.items():
            packs.append({
                "id": pack_config["id"],
                "name": pack_config["name"],
                "quota": pack_config["quota"],
                "price": pack_config["price"],
                "validity_days": pack_config["validity_days"]
            })
        return packs

    @classmethod
    def get_plan_by_id(cls, plan_id: str) -> Dict[str, Any] | None:
        """
        Get a specific plan by ID.

        Args:
            plan_id: Plan identifier ('free', 'pro', 'ultra')

        Returns:
            Plan dictionary or None if not found
        """
        return cls.PLANS.get(plan_id)

    @classmethod
    def get_quota_pack_by_id(cls, pack_id: str) -> Dict[str, Any] | None:
        """
        Get a specific quota pack by ID.

        Args:
            pack_id: Pack identifier ('pack_10', 'pack_50')

        Returns:
            Quota pack dictionary or None if not found
        """
        return cls.QUOTA_PACKS.get(pack_id)

    @classmethod
    def get_plan_quota(cls, plan_id: str) -> int:
        """
        Get the monthly quota for a plan.

        Args:
            plan_id: Plan identifier

        Returns:
            Monthly quota count (0 for free)
        """
        plan = cls.PLANS.get(plan_id)
        return plan["quota"] if plan else 0

    @classmethod
    def calculate_price(
        cls,
        plan_id: str,
        period: str
    ) -> int:
        """
        Calculate price for a plan and period.

        Args:
            plan_id: Plan identifier
            period: Billing period ('monthly', 'quarterly', 'yearly')

        Returns:
            Price in cents
        """
        plan = cls.PLANS.get(plan_id)
        if not plan:
            return 0
        return plan["prices"].get(period, 0)

    @classmethod
    def get_full_pricing_info(cls) -> Dict[str, Any]:
        """
        Get complete pricing information including plans and quota packs.

        Returns:
            Dictionary with plans and quota_packs
        """
        return {
            "plans": cls.PLANS,
            "quota_packs": cls.QUOTA_PACKS
        }
