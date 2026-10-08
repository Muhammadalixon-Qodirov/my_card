from rest_framework.throttling import AnonRateThrottle


class AdminLoginThrottle(AnonRateThrottle):
    scope = "admin_login"
    rate = "10/min"
