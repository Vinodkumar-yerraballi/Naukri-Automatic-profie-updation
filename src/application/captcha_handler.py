class CaptchaHandler:
    """
    Handles CAPTCHA and OTP/security verification situations.

    This class does not bypass security challenges.
    It only detects them and stops the automation.
    """

    CAPTCHA_KEYWORDS = [
        "captcha",
        "recaptcha",
        "hcaptcha",
        "verify you are human",
        "verification required",
        "security check"
    ]

    OTP_KEYWORDS = [
        "otp",
        "one time password",
        "verification code",
        "enter code",
        "verify phone"
    ]
    def __init__(self):
        self.challenge_detected =False
        self.challenge_type = None
    def detect_challenge(self,page_text:str)->bool:
        """
        Detect CAPTCHA or OTP/security challenges
        from visible page text.
        """
        if not page_text:
            return False
        text=page_text.lower()
        for keyword in self.CAPTCHA_KEYWORDS:
            if keyword in text:
                self.challenge_detected=True
                self.challenge_type="CAPTCHA"
                return True
        for keyword in self.OTP_KEYWORDS:
            if keyword in text:
                self.challenge_detected= True
                self.challenge_type="OTP"
                return True
        self.challenge_detected=False
        self.challenge_type=None
        return False
    def get_challenge_type(self)->str:
        """
        Return the detected challenge type.
        """
        return self.challenge_type
    def requires_manual_action(self)->bool:
        """
        Return True when manual user intervention is required.
        """
        return self.challenge_detected
    def get_status(self)->dict:
        """
        Return the current security challenge status.
        """
        return {
            "challenge_detected": self.challenge_detected,
            "challenge_type": self.challenge_type,
            "requires_manual_action": self.requires_manual_action()
        }
