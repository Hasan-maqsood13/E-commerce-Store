from django.shortcuts import render, redirect, HttpResponse
from django.http import JsonResponse, HttpResponseForbidden
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.hashers import make_password, check_password
from django.conf import settings
from django.core.mail import send_mail
from .models import *
from ecommerce_store.settings import EMAIL_HOST_USER
import random
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils.timezone import make_aware
from datetime import datetime
from django.core import serializers
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.utils.dateparse import parse_datetime
from django.db.models import Sum
# import stripe
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import *
from django.utils.timezone import make_aware
from datetime import datetime
from django.urls import reverse
from django.utils import timezone


from django.shortcuts import render, redirect, HttpResponse, get_object_or_404
from django.contrib.auth.hashers import make_password, check_password
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware
from urllib.parse import unquote
from django.core.mail import send_mail
from django.utils.text import slugify
from django.contrib import messages
from django.core import serializers
from django.utils import timezone
from django.db.models import Sum
from django.conf import settings
from datetime import timedelta
from datetime import datetime
from .models import *
import random
import json
import re


# stripe.api_key = settings.STRIPE_TEST_SECRET_KEY  # Your Stripe secret key

def generate_verification_code(length=8):
    """Generate a random 4-digit numeric code"""
    return str(random.randint(1000, 9999))


#Create your Views here
def home(request):
    return render(request, 'store/index.html')