from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional

from ..models.models import ReportSubscription, Report, ReportType, ReportFormat, ReportStatus
from .generate_report import ReportGenerator

class SubscriptionHandler:
    def __init__(self, db: Session):
        self.db = db
        self.report_generator = ReportGenerator(db)

    async def process_subscriptions(self) -> None:
        """Process all active subscriptions that are due for delivery."""
        active_subscriptions = self.db.query(ReportSubscription).filter(
            and_(
                ReportSubscription.active == True,
                ReportSubscription.next_delivery <= datetime.utcnow()
            )
        ).all()

        for subscription in active_subscriptions:
            try:
                await self.generate_subscription_report(subscription)
                self._update_subscription_success(subscription)
            except Exception as e:
                self._update_subscription_error(subscription, str(e))

    async def generate_subscription_report(self, subscription: ReportSubscription) -> Optional[Report]:
        """Generate a report for a subscription."""
        end_date = datetime.utcnow()
        start_date = self._calculate_start_date(subscription.frequency, end_date)

        report = Report(
            type=subscription.frequency,
            format=subscription.format,
            start_date=start_date,
            end_date=end_date,
            user_id=subscription.user_id
        )
        self.db.add(report)
        self.db.commit()

        try:
            await self.report_generator.generate_report(report)
            return report
        except Exception as e:
            report.status = ReportStatus.FAILED
            report.error_message = str(e)
            self.db.commit()
            raise

    def _calculate_start_date(self, frequency: ReportType, end_date: datetime) -> datetime:
        """Calculate the start date based on the report frequency."""
        if frequency == ReportType.DAILY:
            return end_date - timedelta(days=1)
        elif frequency == ReportType.WEEKLY:
            return end_date - timedelta(weeks=1)
        elif frequency == ReportType.MONTHLY:
            return end_date - timedelta(days=30)
        else:  # COMPREHENSIVE
            return end_date - timedelta(days=90)

    def _update_subscription_success(self, subscription: ReportSubscription) -> None:
        """Update subscription after successful report generation."""
        subscription.last_delivery = datetime.utcnow()
        subscription.next_delivery = self._calculate_next_delivery(subscription.frequency)
        subscription.delivery_count += 1
        subscription.error_count = 0
        subscription.last_error = None
        self.db.commit()

    def _update_subscription_error(self, subscription: ReportSubscription, error: str) -> None:
        """Update subscription after failed report generation."""
        subscription.error_count += 1
        subscription.last_error = error
        subscription.next_delivery = datetime.utcnow() + timedelta(hours=1)  # Retry in 1 hour
        self.db.commit()

    def _calculate_next_delivery(self, frequency: ReportType) -> datetime:
        """Calculate the next delivery date based on frequency."""
        now = datetime.utcnow()
        if frequency == ReportType.DAILY:
            return now + timedelta(days=1)
        elif frequency == ReportType.WEEKLY:
            return now + timedelta(weeks=1)
        elif frequency == ReportType.MONTHLY:
            return now + timedelta(days=30)
        else:  # COMPREHENSIVE
            return now + timedelta(days=90) 