from django import forms


class MultipleFileInput(forms.ClearableFileInput):
    # Django looks at this flag to decide how to handle the input internally
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        # Checks if data is a list of files
        if isinstance(data, (list, tuple)):
            # Run validatoin on each file via looping
            result = [single_file_clean(d, initial) for d in data]
        else:
            # Run validation on one single file
            result = single_file_clean(data, initial)
        # Return a list of cleaned files or a single cleaned file
        return result
