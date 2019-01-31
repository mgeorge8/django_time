from django import template

register = template.Library()

@register.filter
def get_obj_attr(obj, attr):
    return getattr(obj, attr)

def phonenumber(value):
    phone = '(%s) %s - %s' %(value[0:3],value[3:6],value[6:10])
    return phone

register.filter('phonenumber', phonenumber)
