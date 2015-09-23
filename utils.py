from DateTime.DateTime import DateTime
from Products.Archetypes.event import ObjectInitializedEvent
from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from kss.core.BeautifulSoup import BeautifulSoup, BeautifulStoneSoup
from ocw.publishing.browser.edxcourseconversion.assessmentconversion import *
from ocw.publishing.browser.edxcourseconversion.config import CLONED_COURSE_PATH, \
    TAG_REPLACEMENTS, PULLED_FILE_PATH, BACK_BUTTON, CONTINUE_BUTTON, FLP_BUTTON_TAG, \
    ALLOWED_IMAGE_TYPES, MEDIA_ASSET_TYPES
from zLOG import LOG, INFO, DEBUG
import os
import re
import string
import zope.event

def getCourseDetails(course, git_url):
    ''' Function to get cloned directory path and course url'''
    
    LOG('getCourseDetails : ', INFO, 'Started')
    try:   
        course_url = '/Plone' + course             # creating the Course Url
        cloned_dir = string.replace(git_url.split('/')[1], '.git', '')    
        cloned_dir_path = CLONED_COURSE_PATH + '/' + cloned_dir     # creating the Cloned Course Directory Path
        return course_url, cloned_dir_path
    except Exception, e:
            LOG('createSectionFromBackend : ', INFO, str(e))
            
def createId(id):
        ''' Function to create the id of the section as per the business rules'''
        
        return string.lower(string.replace(id, '_', '-').replace(' ', '-').replace("'", ""))
    
def listOfTagDicts(course_xml):
    ''' Function to create the id of the section as per the business rules'''
    
    try:  
        soup = BeautifulSoup(open(course_xml))                 
        tag_list = []
               
        for tag in soup.findAll():
            if tag.name != 'course':     # Check to remove the tags like <course> where there is no url_name attribute
               tag_list.append({createId(tag.get('url_name')):tag.name}) 
        return tag_list
    except Exception, e:
            LOG('createSectionFromBackend : ', INFO, str(e))
    
def createSectionFromBackend(id, title, obj, parent, short_page_title=None):
    ''' Function to create Sections from the backend '''
    
    LOG('createSectionFromBackend : ', INFO, 'Started')
    try: 
        if short_page_title == None: short_page_title = title       # to set the FLP Title in the bread crumb
        
        obj.invokeFactory(type_name='CourseSection',
                                 id=id,
                                 title=title,
                                 short_page_title=short_page_title,
                                 parent_module=parent,
                                         )
        section_obj = getattr(obj, id)                   
        section_obj.unmarkCreationFlag()
        zope.event.notify(ObjectInitializedEvent(section_obj))
        return  section_obj
    
    except Exception, e:
        LOG('createSectionFromBackend : ', INFO, str(e))
            
def createMediaResourceFromBackend(context, obj, video_id, video_title):
    ''' Function to create Media Resource from backend '''
    
    LOG('createMediaResourceFromBackend : ', INFO, 'Started')
    try: 
        obj.invokeFactory(type_name='MediaResource',
                                                    id=video_id,
                                                    title=video_title,
                                                    template_type='Embed',
                                                    excludeFromNav=True,
                                                    description='Media Resource:',
                                                    always_publish=True
                                               )  
        media_ResourceObj = getattr(obj, video_id)
                                         
        portal_membership = getToolByName(context, 'portal_membership')
          
        if not portal_membership.isAnonymousUser():
             member = portal_membership.getAuthenticatedMember()
             media_ResourceObj.changeOwnership(member.getUser(), 1)
             
        media_ResourceObj.unmarkCreationFlag()                    
        zope.event.notify(ObjectInitializedEvent(media_ResourceObj))
                       
        LOG('media_ResourceObj : ', INFO, media_ResourceObj.inline_embed_id)
        return  media_ResourceObj     
    except Exception, e:
       LOG('createMediaResourceFromBackend : ', INFO, str(obj.short_page_title) + ": " + str(e))
     
def addBackgroundImageFromBackend(section_obj, image_obj, image_format):
    ''' Function to add Media Asset from backend '''
    
    LOG('addBackgroundImageFromBackend : ', INFO, 'Started')
    try:  
        newAssetId = createId('Background Image-OCW-' + image_format)
        section_obj.invokeFactory(
               type_name='OCWMediaAsset',
               id=newAssetId,                       
               media_asset_type='Background Image',                   
               media_asset_source='OCW',
               media_location='',
               media_format=image_format,
               media_size='',
               )
        background_image_obj = getattr(section_obj, newAssetId)
        background_image_obj.setFile_reference(image_obj.UID())
        background_image_obj.unmarkCreationFlag()
        zope.event.notify(ObjectInitializedEvent(background_image_obj))
        
    except Exception, e:
       LOG('addBackgroundImageFromBackend : ', INFO, str(section_obj.id) + ": " + str(e))
    return

def addMediaAssetFromBackend(obj, youtube_id):
    ''' Function to add Media Asset from backend '''
    
    LOG('addMediaAssetFromBackend : ', INFO, 'Started')
    try:        
        for asset_type in MEDIA_ASSET_TYPES:
            asset_format = 'stream'
            
            if asset_type == 'Video':
                asset_source = 'YouTube' 
            else:
                asset_source = '3Play YouTube id'    
            
            asset_id = asset_type + '-' + asset_source + '-' + asset_format
            
            obj.invokeFactory(type_name='OCWMediaAsset',
                                       id=asset_id,
                                       media_asset_type=asset_type,
                                       media_asset_source=asset_source,
                                       media_location=youtube_id,
                                       media_format=asset_format,
                                    )
            assetobj = getattr(obj, asset_id)
            assetobj.unmarkCreationFlag()
            zope.event.notify(ObjectInitializedEvent(assetobj))
        
    except Exception, e:
       LOG('addMediaAssetFromBackend : ', INFO, str(obj.id) + ": " + str(e))
    return

def addResourcesFromBackend(obj, context, portal_catalog, cloned_dir_path, content):
    ''' Function to add Images/Resources from the backend '''
    
    LOG('addResourcesFromBackend : ', INFO, 'Started')  
    try: 
        images_list = content.findAll('img')
        anchor_link_list = content.findAll('a')     # List of all <a> tags in the Xml File
        
        for link in anchor_link_list:
           file_name = link.get('href').split('/')[-1]
           
           if '.' in file_name:
               file_type = file_name.split('.')[-1] 
               file = cloned_dir_path + link.get('href')
                          
               if file_type not in ALLOWED_IMAGE_TYPES:           
                 file_path = file.encode("utf-8")
                 
                 if (os.path.isfile(file_path)) :              
                    file_obj = open(file_path, "rb") 
                    if os.path.isfile(PULLED_FILE_PATH) == True:
                       path = "/".join(obj.getPhysicalPath())
                       file_list = portal_catalog.searchResults({'meta_type' : 'OCWFile'}, path={'query': path  , 'depth': 1}, getId=file_name)
                       if file_list:
                           ocw_file_obj = file_list[0].getObject()
                           link['href'] = "/" + ocw_file_obj.virtual_url_path()
                           LOG('addResourcesFromBackend : ', INFO, str(obj.id) + ": " + str(e))
                       else: 
                           ocw_file_obj = createFileFromBackend(obj, context, file_name, file_obj)
                           link['href'] = "/" + ocw_file_obj.virtual_url_path()    
                    else: 
                        ocw_file_obj = createFileFromBackend(obj, context, file_name, file_obj)
                        link['href'] = "/" + ocw_file_obj.virtual_url_path()
                    
               else: images_list.append(link)
                    
        addImageFromBackend(obj, context, portal_catalog, images_list, cloned_dir_path)
        
    except Exception, e:
       LOG('addResourcesFromBackend : ', INFO, str(obj.id) + ": " + str(e))       
    return content       
             
def createFileFromBackend(obj, context, fileName, file_obj):
    ''' Function to create Image from the backend '''
    
    LOG('Creating File Starts: ', INFO, str(fileName))
    try:
            obj.invokeFactory(type_name='OCWFile',
                                        id=fileName,
                                        title=fileName,
                                        file=file_obj,
                                        excludeFromNav=True,
                                        description='Resource:',
                                        always_publish=True
                                   )
            ocw_file_obj = getattr(obj, fileName)         
            portal_membership = getToolByName(context, 'portal_membership')
               
            if not portal_membership.isAnonymousUser():
                member = portal_membership.getAuthenticatedMember()
                ocw_file_obj.changeOwnership(member.getUser(), 1)
                
            ocw_file_obj.unmarkCreationFlag()                    
            zope.event.notify(ObjectInitializedEvent(ocw_file_obj))      
            return  ocw_file_obj
        
    except Exception, e:
      LOG('createFileFromBackend : ', INFO, str(obj.id) + ": " + str(e))

def addImageFromBackend(obj, context, portal_catalog, images_list, cloned_dir_path):
    ''' Function to add Images from the backend '''
    
    LOG(' addImageFromBackend: ', INFO, 'Started')        
    added_image_list = []
    try:
        for img in images_list:
            location = ''
            
            if img.name == 'img': location = img.get('src')                     
            else: location = img.get('href')
            
            imagename = location.split("/")[-1]
            img_path = (cloned_dir_path + location).encode('utf-8')
            
            if os.path.isfile(img_path):
                
                if imagename not in added_image_list : # Check to fix the figure links with images from different section 
                   image_obj = open(img_path, "rb")
                    
                   if os.path.isfile(PULLED_FILE_PATH) == True:
                       path = "/".join(obj.getPhysicalPath())
                       image_list = portal_catalog.searchResults({'meta_type' : 'OCWImage'}, path={'query': path  , 'depth': 1}, getId=str(imagename))
                       added_image_list.append(imagename)
                       
                       if image_list:
                           ocw_image_obj = image_list[0].getObject()
                           if img.name == 'img': img['src'] = "/" + ocw_image_obj.virtual_url_path()
                           else : img['href'] = "/" + ocw_image_obj.virtual_url_path() + "/" + imagename
                       
                       else:   
                          ocw_image_obj = createImageFromBackend(obj, context, imagename, image_obj)
                          added_image_list.append(imagename)
                          
                          if img.name == 'img': img['src'] = "/" + ocw_image_obj.virtual_url_path()
                          else : img['href'] = "/" + ocw_image_obj.virtual_url_path() + "/" + imagename
                   else:
                       ocw_image_obj = createImageFromBackend(obj, context, imagename, image_obj)
                       added_image_list.append(imagename)
                       
                       if img.name == 'img': img['src'] = "/" + ocw_image_obj.virtual_url_path()
                       else : img['href'] = "/" + ocw_image_obj.virtual_url_path() + "/" + imagename
                       
                elif img.name == 'img':     img['src'] = "/" + obj.virtual_url_path() + "/" + imagename                        
                else:   img['href'] = "/" + obj.virtual_url_path() + "/" + imagename
                
    except Exception, e:
        LOG('addImageFromBackend : ', INFO, str(obj.short_page_title) + ": " + str(e))
    return 

def createImageFromBackend(obj, context, imagename, image_obj):
    ''' Function to create Image from the backend '''
    
    LOG('createImageFromBackend : ', INFO, 'Started')   
    try: 
        obj.invokeFactory(type_name='OCWImage',
                                                id=imagename,
                                                title=imagename,
                                                image=image_obj,
                                                excludeFromNav=True,
                                                description='Image: ',
                                                always_publish=True
                                           )
        ocw_image_obj = getattr(obj, imagename)                            
        portal_membership = getToolByName(context, 'portal_membership')
           
        if not portal_membership.isAnonymousUser():
            member = portal_membership.getAuthenticatedMember()
            ocw_image_obj.changeOwnership(member.getUser(), 1)
            
        ocw_image_obj.unmarkCreationFlag()                    
        zope.event.notify(ObjectInitializedEvent(ocw_image_obj))
        
    except Exception, e:
      LOG('createImageFromBackend : ', INFO, str(obj.short_page_title) + ": " + str(e))
    return ocw_image_obj

def addSubsequentialLinksOnSectionPages(tlp_obj, list):
    ''' Function to add links of TLPs and FLPs in parent level '''
    
    LOG('addSubsequentialLinksOnSectionPages : ', INFO, 'Started')
    body_text = '' 
    try:        
        body_text = '<p><strong>' + tlp_obj.title + '</strong></p>'     # link of TLP   
        body_text += '<ul class="arrow">'   # list of link of FLP related to the TLP
         
        for obj_dict in list:
            title, obj = obj_dict.items()[0]  
            body_text += '<li><a href="/' + obj.virtual_url_path() + '">' + title + '</a></li>'
                
        body_text += '</ul>'      
          
    except Exception, e:
       LOG('addSubsequentialLinksOnSectionPages : ', INFO, str(tlp_obj.title) + ": " + str(e))       
    return  body_text   

def setBodyTextOnSectionPages(first_tlp_obj, section_obj, tlp_text, nav_obj):
    ''' Function to set the body text of section pages to display list of TLPs and FlPs links '''
    
    LOG('setBodyTextOnSectionPages : ', INFO, 'Started')
    try:     
        top_nav_text = '<div class="navigation progress">' + nav_obj.back_button + nav_obj.continue_button + '</div>'
        body_text = top_nav_text + str(tlp_text) + nav_obj.bottom_nav_buttons
        section_obj.setText(str(body_text))
        section_obj.reindexObject()
         
    except Exception, e:
       LOG('setBodyTextOnSectionPages : ', INFO, str(section_obj.title) + ": " + str(e)) 
    return
    
def getSectionObject(portal_catalog, section_id, course_url):
    '''Function to find if the section exist and returns the list of section objects'''
    
    LOG('getSectionObject : ', INFO, 'Started')
    section_obj_list = []
    try:
        sections = portal_catalog.searchResults({'meta_type' : 'CourseSection'}, path={'query': course_url, 'depth': 5 }, getId=str(section_id))        
        if sections:          
            for section in sections:
                section_obj_list.append(section.getObject())                 
        return section_obj_list
    
    except Exception, e:
           LOG(' : ', INFO, str(section_id) + ": " + str(e))
           
def getMediaResourceObject(portal_catalog, video_id, path):
    '''Function to find if the section exist and returns the list of section objects'''
    
    LOG('getMediaResourceObject : ', INFO, 'Started')
    try:
        mediaresource = portal_catalog.searchResults({'meta_type' : 'MediaResource'}, path={'query': path, 'depth': 1}, getId=str(video_id))       
        LOG('mediaresource : ', INFO, str(mediaresource))
        if mediaresource: 
            LOG('mediaresource[0] : ', INFO, str(mediaresource[0].getObject()))         
            return mediaresource[0].getObject() 
    
    except Exception, e:
           LOG(' : ', INFO, str(video_id) + ": " + str(e))
    return 
