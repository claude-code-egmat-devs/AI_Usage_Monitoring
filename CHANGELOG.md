# Changelog

All notable changes to AI Usage Monitoring will be documented in this file.

## [1.0.0] - 2026-01-12

### Added
- Initial release
- Centralized logging for all VPS apps
- Daily report generation with Teams notifications
- Real-time alert monitoring for threshold breaches
- Budget tracking and alerts
- Support for multiple apps
- Power Automate integration for Teams notifications

### Components
- `lib/teams_notifier.py` - Teams notification module
- `lib/shared_logger.py` - Shared logging module for apps
- `services/daily_report.py` - Daily report generator
- `services/alert_monitor.py` - Alert monitoring service
- `config/settings.json` - Configuration file

### Alerts
- Daily cost warning ($5 threshold)
- Daily cost critical ($10 threshold)
- Monthly budget warning (80% of $100)
- Error spike detection (5+ errors in 1 hour)
