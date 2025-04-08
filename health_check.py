# health_check.py
def register_health_check(app):
    @app.route("/health")
    def health():
        return "OK", 200