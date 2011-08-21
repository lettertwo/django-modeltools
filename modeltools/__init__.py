import os.path
import re


class PropertyFormatter(object):
    """
    An object that lazily formats properties of a model, exposing them as
    dictionary keys.
    """
    def __init__(self, model, lowercase, nonwordchars, word_delimiter='_'):
        self.__model = model
        self.__lowercase = lowercase
        self.__nonwordchars = nonwordchars
        self.__word_delimiter = word_delimiter

    def __getitem__(self, key):
        prop_chain = key.split('__')
        value = self.__model
        while prop_chain:
            try:
                value = getattr(value, prop_chain.pop(0))
            except AttributeError:
                value = None
            if value is None:
                break
        value = str(value)
        if self.__lowercase:
            value = value.lower()
        if not self.__nonwordchars:
            value = re.sub('[^\w\s]+', '', value)
        return re.sub('\s+', self.__word_delimiter, value)

    def keys(self):
        keys = self._get_keys(self.__model)
        self._add_related_keys(self.__model, keys)
        return keys

    @classmethod
    def _add_related_keys(cls, model, keys, prefixes = [], checked_models = []):
        # Prevent recursion from related models referencing each other.
        if model in checked_models: return
        checked_models.append(model)
        for field in model._meta.fields:
            if field.rel is not None:
                m = getattr(model, field.name)
                if m is not None:
                    pre = prefixes[:]
                    pre.append(field.name)
                    p = '__'.join(pre)
                    keys += ['%s__%s' % (p, k) for k in cls._get_keys(m)]
                    cls._add_related_keys(m, keys, pre, checked_models)

    @classmethod
    def _get_keys(cls, model):
        return model.__dict__.keys()


def format_filename(pattern, add_extension=True, lowercase=True, nonwordchars=False, word_delimiter='_'):
    """
    Creates a method to be used as a value for Django models' upload_to
    argument. The returned method will format a filename based on properties of
    the model. Properties of related models may also be used by separating the 
    property name from the model name with '__'.
    
    Usage:
        thumbnail = models.ImageField(upload_to=format_filename('profile_images/{group__name}_{last_name}_{first_name}'))
    """
    def upload_to(self, old_filename):
        extension = os.path.splitext(old_filename)[1]
        wrapper = PropertyFormatter(self, lowercase=lowercase, nonwordchars=nonwordchars, word_delimiter=word_delimiter)
        filename = pattern.format(**wrapper)
        if add_extension:
            filename += extension
        return filename

    return upload_to


class Enum(object):
    """
    A class for easily creating enumeration types.
    
    Usage:
    
        # models.py
        class MyModel(models.Model):
            
            Color = Enum(
                RED=('r', 'Red'),
                GREEN=('g', 'Green'),
                BLUE=('b', 'Blue'),
            )

            color = models.CharField(max_length=1, choices=Color.choices())
        
        # Elsewhere...
        m = MyModel.objects.filter(color=MyModel.Color.RED)
    
    """
    
    def __init__(self, **kwargs):
        """
        Accepts kwargs where the keyword is the constant name and the value is
        a tuple containing the ENUM value and a label
        """
        self.__kwargs = kwargs
        for key, value in kwargs.items():
            setattr(self, key, value[0])
        self.__choices = kwargs.values()

    def choices(self):
        """
        Returns a list formatted for use as field choices.
        (See https://docs.djangoproject.com/en/dev/ref/models/fields/#choices)
        """
        return self.__choices

    def keys(self):
        return self.__kwargs.keys()

    def values(self):
        return [val[0] for val in self.__kwargs.values()]

    def labels(self):
        return [val[1] for val in self.__kwargs.values()]

    def get_label(self, enum_value):
        for key, value in self.__choices:
            if enum_value == key:
                return value
