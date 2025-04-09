DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

INSTALLED_APPS = [
    "easy_images",
    "tests.easy_images_tests",
]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": "/tmp/easy-images-tests/",
        },
    }
}
USE_TZ = True
SECRET_KEY = "test"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,  # Allows finding templates in installed apps (like easy_images)
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            # Ensure easy_images tags are loaded automatically if needed,
            # or rely on {% load easy_images %} in templates. APP_DIRS=True is key.
        },
    }
]
SECRET_KEY = "test"
