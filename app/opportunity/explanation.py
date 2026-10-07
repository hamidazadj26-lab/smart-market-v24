"""Structured explanations for opportunity decisions."""

def explain(score):
    unknown = [k for k, v in score.dimensions.items() if v is None]
    return {
        'score': score.total,
        'priority': score.priority,
        'confidence': score.confidence,
        'coverage': score.coverage,
        'dimensions': score.dimensions,
        'reasons': score.reasons,
        'unknown_dimensions': unknown,
        'limitations': [
            'رقابت، تکرارپذیری و قابلیت اتکای طرفین تا زمانی که داده مشاهده‌شده وجود نداشته باشد نامشخص می‌مانند.',
            'پتانسیل حاشیه سود تا زمان وجود قیمت خرید، قیمت فروش و هزینه‌های معامله محاسبه قطعی نشده است.',
            'امتیاز فرصت پیش‌بینی نتیجه معامله نیست.',
        ],
    }
