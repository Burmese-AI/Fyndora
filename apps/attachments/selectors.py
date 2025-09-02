from .models import Attachment

def get_attachment(pk):
    return Attachment.objects.get(pk=pk)