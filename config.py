CLONED_COURSE_PATH = "/files/OCWFileShare/Applications/Edx"

PULLED_FILE_PATH = "/files/OCWFileShare/Applications/Edx/pulling.txt"

TAG_REPLACEMENTS = {    
     '</html>':'',
     '<script src="/static/latex2edx.js" type="text/javascript">': '',
     '</script>':'',
     '<h2 class="problem-header">':'<h2 class="subhead">',
     '[mathjaxinline]':'\(',
     '[mathjax]':'\[',
     '[/mathjaxinline]':'\)',
     '[/mathjax]' :'\]',
     }

BACK_BUTTON = '<button %s type="button" onclick="window.location.assign('"'%s'"');" >Back<span>%s</span></button> '

CONTINUE_BUTTON = '<button %s type="button" onclick="window.location.assign('"'%s'"');" >Continue<span>%s</span></button> '

BACK_LI_TAG = '<li %s><a href='"'%s'"';><<span>%s</span></a></li>'

CONTINUE_LI_TAG = '<li %s><a href='"'%s'"';>><span>%s</span></a></li>'

FLP_BUTTON_TAG =  '<li id="%s" %s><a href='"'%s'"'>%s<span>%s</span></a></li>'

ALLOWED_IMAGE_TYPES = ('jpg', 'pct', 'pic', 'pict', 'xwd', 'xpm', 'xbm', 'tif', 'tiff', 'rgb', 'ras', 'ppm', 'pnm', 'png', 'pgm' , 'pbm', 'jpe', 'jpeg', 'jpg', 'gif', 'bmp')

MEDIA_ASSET_TYPES = ('Video', '3Play')
