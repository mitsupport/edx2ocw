from DateTime.DateTime import DateTime
from Products.Archetypes.event import ObjectInitializedEvent
from Products.CMFCore.utils import getToolByName
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from kss.core.BeautifulSoup import BeautifulSoup, BeautifulStoneSoup
from ocw.publishing.browser.edxcourseconversion.assessmentconversion import *
from ocw.publishing.browser.edxcourseconversion.config import CLONED_COURSE_PATH, \
    TAG_REPLACEMENTS, PULLED_FILE_PATH, BACK_BUTTON, CONTINUE_BUTTON, FLP_BUTTON_TAG, \
    BACK_LI_TAG, CONTINUE_LI_TAG
from ocw.publishing.browser.edxcourseconversion.utils import *
from zLOG import LOG, INFO, DEBUG
import HTMLParser
import os
import re
import string
import zope.event


class StudioEdxCourseConversion:  

    def __init__(self, context, request, course_URL, cloned_dir_path):
        self.context = context
        self.request = request
        self.portal_catalog = getToolByName(self.context, 'portal_catalog')
        self.exception_list = []
        self.course_url = course_URL
        self.cloned_dir_path = cloned_dir_path   
        self.course_file_path = self.cloned_dir_path + '/course.xml'                     
        self.pulling = os.path.isfile(PULLED_FILE_PATH)
        self.problem_count = 0;
        self.solution_count = 0;
        self.problem_btns_count = 1;
        
    def createListofTagDictionary(self):
        '''Function to get the Course URL provided as input to the user'''
        
        LOG('StudioEdxCourseConversion : ', INFO, 'Started')
        try:            
            self.id_obj_dict = {}    
            self.vertical_tag_list = [] 
            soup = BeautifulSoup(open(self.course_file_path))    
            self.chap_seq_vert_tag_list = [] 
                  
            for chapter in soup.findAll('chapter', {'visible_to_staff_only': None}):
                self.chap_seq_vert_tag_list.append({createId(chapter.get('url_name')) : (chapter.name, chapter.get('display_name'))}) 
                for sequential in chapter.findAll('sequential', {'visible_to_staff_only': None}):
                    self.chap_seq_vert_tag_list.append({createId(sequential.get('url_name')) : (sequential.name, sequential.get('display_name'))})
                    for vertical in sequential.findAll('vertical', {'visible_to_staff_only': None}): 
                        self.chap_seq_vert_tag_list.append({createId(vertical.get('url_name')) : (vertical.name, vertical.get('display_name'))})
                 
        except Exception, e:
            self.exception_list.append('createListofTagDictionary : ' + str(e))
            LOG('createListofTagDictionary : ', INFO, str(e))          
        return self.getFileContents()    

    def getFileContents(self):
        ''' Function to read the contents from the Edx Course structure and creation of sections '''
          
        LOG('Course creation started : ', INFO, 'getFileContents')
        course = self.portal_catalog.searchResults({'meta_type' : ('Course')},
                                                   path={'query' : self.course_url })     # Catalog search to find the course object
        try:       
            if len(course) == 1:
                self.flp_links_dict = {}
                course_obj = course[0].getObject()
                soup = BeautifulStoneSoup(open(self.course_file_path))
                # code to add background images in video 
                video_image = string.replace(self.cloned_dir_path , CLONED_COURSE_PATH + '/' , '').split('-')[-1]+'_video_background_image'
                video_image_path =  self.cloned_dir_path +'/static/video_background_image'
                background_image_obj = None
                
                if os.path.isdir(video_image_path):
                    video_background_image = os.listdir(video_image_path)[0]
                    self.image_format = video_background_image.split('.')[-1].upper()
                    video_image_obj = open(video_image_path + '/' + video_background_image, "rb")
                    background_image_obj = createImageFromBackend(course_obj, self.context, video_image, video_image_obj)
                    
                # list of all Chapter tags will be used to create course section 
                self.chapter_counter = 1
                html_parser = HTMLParser.HTMLParser()                         
                for chapter in soup.findAll('chapter', {'visible_to_staff_only': None}): 
                    try:                       
                        section = chapter.get('url_name') 
                        section_id = createId(section)
                        section_title = str(self.chapter_counter) + ' ' + html_parser.unescape(chapter.get('display_name'))
                        section_obj = createSectionFromBackend(section_id, section_title, course_obj, course_obj)                      
                        self.id_obj_dict[section_id] = section_obj
                        LOG('Section_Title : ', INFO, section_obj.title)                    
                     
                        # list of all Sequential tags will be used to create course TLP
                        self.sequential_counter = 1
                        self.sequential_text = ''                        
                        for sequential in chapter.findAll('sequential', {'visible_to_staff_only': None}):
                            try:
                                sequential_id = createId(sequential.get('url_name'))
                                sequential_title = str(self.chapter_counter) + '.' + str(self.sequential_counter) + ' ' + html_parser.unescape(sequential.get('display_name'))
                                tlp_obj = createSectionFromBackend(sequential_id, sequential_title, section_obj, course_obj)                            
                                                        
                                if self.sequential_counter == 1: first_tlp_obj = tlp_obj
                                
                                tlp_obj.list_in_left_nav = True
                                self.id_obj_dict[sequential_id] = tlp_obj
                                LOG('TLP_Title : ', INFO, tlp_obj.title)
                                
                                # Creation of Course FLP using Vertical tags
                                all_vertical_list = []   # List of dictionary containing the the FLP number as key and FLP obj as value 
                                vertical_counter = 1   
                                self.vertical_tag_list = sequential.findAll('vertical', {'visible_to_staff_only': None})
                                 
                                for vertical in self.vertical_tag_list:
                                    try:  
                                        self.vertical_numbering = str(self.chapter_counter) + '.' + str(self.sequential_counter) + '.' + str(vertical_counter) # To append the section no. to the section title
                                        flp_short_page_title = self.vertical_numbering + ' ' + html_parser.unescape(vertical.get('display_name'))
                                        flp_id = createId(vertical.get('url_name'))
                                                     
                                        if self.vertical_tag_list.index(vertical) > 0:
                                            flp_obj = createSectionFromBackend(flp_id, sequential_title, tlp_obj, course_obj, flp_short_page_title)                              
                                            flp_obj.always_publish = True,
                                        else :
                                            flp_obj = tlp_obj
                                            
                                        all_vertical_list.append({flp_short_page_title : flp_obj}) # list of all FLP object under one TLP/Sequential tags

                                        self.id_obj_dict[flp_id] = flp_obj 
                                        LOG('FLP_Title : ', INFO, flp_obj.title) 
                                        vertical_counter += 1  
                                        self.flag = False
                                        for tag in vertical.findAll(['html', 'problem', 'video'], {'visible_to_staff_only': None}):
                                            self.setBodyTextonTlpandFlpSections(tag, flp_obj, background_image_obj)
                                                                      
                                        top_nav_text, bottom_nav_text = self.createNavigationButtons(flp_obj)
                                        flp_body_text = top_nav_text + flp_obj.getText().decode('utf-8') + bottom_nav_text
                                        flp_obj.setText(flp_body_text)
                                        flp_obj.reindexObject()                                        
                                        
                                    except Exception, e:
                                        self.exception_list.append(str(tlp_obj.title) + ": " + str(e))
                                        LOG('Exception in creation of FLP : ', INFO, str(e))
                                
                                # creating the body text on Section Pages
                                self.sequential_text += addSubsequentialLinksOnSectionPages(tlp_obj, all_vertical_list)    # code to create the links of sequential and sub-sequential
                                self.sequential_counter += 1
                            
                            except Exception, e:
                                self.exception_list.append(str(section_obj.title) + ": " + str(e))
                                LOG('Exception occurs in creation of Sequential : ', INFO, +str(e))
                        
                        # setting the body text on Section Pages    
                        nav_obj = navigation(section_obj, self.pulling, self.chap_seq_vert_tag_list, self.id_obj_dict)            
                        setBodyTextOnSectionPages(first_tlp_obj, section_obj, self.sequential_text, nav_obj)                
                        self.chapter_counter += 1
                        
                    except Exception, e:
                        self.exception_list.append(str(course_obj.title) + ": " + str(e))
                        LOG('Exception occurs in creation of Chapter : ', INFO, str(e))
                        
                if self.exception_list:  
                    LOG('Following Exceptions occurs : ', INFO, str(self.exception_list))     
                    return 'Following Exceptions occurs : ' + str(self.exception_list)
                
                else:
                    LOG('Course created SucessFully at : ', INFO, str(course_obj.virtual_url_path())) 
                    return 'Course created SucessFully at: ' + str(course_obj.virtual_url_path()) 
                 
            elif len(course) == 0:
                LOG('Course not Found : ', INFO, self.course_url)
                return 'Course not Found : ' + self.course_url
            
            else: 
                course_list = []
                for course_obj in course:
                    course_list.append(course_obj.getObject().virtual_url_path())
                    
                return '   ' + str(len(course_list)) + ' Courses found : ' + str([course_obj.getObject().virtual_url_path() for course_obj in course])
                
        except Exception, e:
            self.exception_list.append(str(course_obj.title) + ": " + str(e))
            LOG('Following Exceptions occurs : ', INFO, str(self.exception_list))
            return 'Following Exceptions occurs : ' + str(self.exception_list)
   
    def setBodyTextonTlpandFlpSections(self, tag , obj, background_image_obj):
        ''' setting the body text on TLP and FLP pages'''
        
        LOG('setBodyTextonTlpandFlpSections : ', INFO, 'Started')
        try:
            body_text = obj.getText() 
            flp_soup = ''          
            
            if tag.name == 'video':
                video_id = createId(tag.get('url_name'))
                media_ResourceObj = createMediaResourceFromBackend(self.context, obj, video_id , tag.get('display_name')) 
                # code to add background images in video 
                if(background_image_obj is not None): 
                    addBackgroundImageFromBackend(media_ResourceObj, background_image_obj, self.image_format)
                
                addMediaAssetFromBackend(media_ResourceObj, tag.get('youtube').split(':')[1])               
                body_text += '<h2 class="subhead">' + tag.get('display_name') + '</h2>' + \
                             '<p>' + media_ResourceObj.inline_embed_id + '</p>'
                obj.has_inline_embed = True
            
            else :
                if tag.name == 'problem': 
                    flp_file = self.cloned_dir_path + '/' + tag.name + '/' + tag.get('url_name') + '.xml'   # Fetching the XML File related to the the FLP\
                    if os.path.isfile(flp_file): 
                        flp_soup = BeautifulSoup(getModifiedAssessmentString(self, flp_file, self.flag))
                        self.flag = True
                                              
                else:                   
                    flp_file = self.cloned_dir_path + '/' + tag.name + '/' + tag.get('filename') + '.html'   # Fetching the XML File related to the the FLP
                    if os.path.isfile(flp_file):  
                        flp_soup = BeautifulStoneSoup(open(flp_file)) 
                         
                LOG('flp_obj.title : ', INFO, obj.title)
                flp_path = '/' + obj.virtual_url_path()        
                flp_soup = addResourcesFromBackend(obj, self.context, self.portal_catalog, self.cloned_dir_path, flp_soup)
                flp_soup = self.modifyHtmlContent(obj, flp_soup, flp_path)
                body_text += str(flp_soup)         
                
            obj.setText(str(body_text))                                        
            obj.reindexObject()
            LOG('setBodyTextonTlpandFlpSections : ', INFO, 'Completed')
        except Exception, e:
            self.exception_list.append(str(obj.short_page_title) + ": " + str(e))
            LOG('setBodyTextonTlpandFlpSections : ', INFO, str(obj.short_page_title) + ": " + str(e))
        return 

    def modifyHtmlContent(self, obj, content, path):
        '''Function to modify and set the content '''   
        
        try:
            LOG('modifyHtmlContent : ', INFO, 'Started')               
            if content != '':
                content = re.sub(r'<html.*', "", str(content))     
                btag_textlist = re.findall('<p>\n<b class="bfseries">(.*)</b>\n</p>', content) 
                if btag_textlist:
                  for text in btag_textlist:    
                      content = string.replace(content, '<p>\n<b class="bfseries">' + text + '</b>\n</p>', '<h2 class="subhead">' + text + '</h2>')
                
                for key, value in TAG_REPLACEMENTS.iteritems():
                    if key in content:
                        content = string.replace(content, key, value)
                
                if '\(' in content or '\[' in content :
                    obj.is_mathml_document = True
                LOG('modifyHtmlContent : ', INFO, 'completed')
            
        except Exception, e:
            self.exception_list.append(str(obj.short_page_title) + ": " + str(e))
            LOG('modifyHtmlContent : ', INFO, str(obj.short_page_title) + ": " + str(e))       
        return content
    
    def createNavigationButtons(self, obj):
        '''Function to create FLP Navigation Buttons ''' 
        
        LOG('createNavigationButtons : ', INFO, 'started')
        btn_counter = 1
        flp_button = ''
        count = 0
        btn_class = ''
        top_nav_buttons = ''
        
        try:
            if self.pulling == True :  
                nav_obj = navigation(obj, self.pulling)          
                body_text = obj.getText()
                soup = BeautifulSoup(body_text)
                for  btn in soup.findAll('li', {"id" : re.compile('flp_btn_') }):
                     flp_button += str(btn) + ' '
            else:
                nav_obj = navigation(obj, self.pulling, self.chap_seq_vert_tag_list, self.id_obj_dict)             
                url = '/' + obj.virtual_url_path()
                            
                for tag_dict in self.chap_seq_vert_tag_list:
                    key, tag = tag_dict.items()[0] 
                    
                    if (obj.id == key) and tag[0] == 'vertical':  # check to match the key with the current FLP Id  
                            url = '/'.join(url.split('/')[:-1])
                            break
                    count += 1
                               
                while btn_counter <= len(self.vertical_tag_list):
                   btn_text = str(self.chapter_counter) + '.' + str(self.sequential_counter) + '.' + str(btn_counter)
                   
                   if self.vertical_numbering == btn_text: btn_class = 'class="button_selected"'
                   else : btn_class = ''
                   btn_title = self.vertical_tag_list[btn_counter - 1].get('display_name')
                   btn_url = ''
                   if btn_counter == 1:
                       btn_url = url
                   else:
                        btn_url = url + '/' + createId(self.vertical_tag_list[btn_counter - 1].get('url_name'))
                        
                   flp_button_id = 'flp_btn_' + str(btn_counter)            
                   flp_button += FLP_BUTTON_TAG % (flp_button_id, btn_class, btn_url, btn_text, btn_title) 
                   btn_counter += 1         
                        
            top_nav_buttons = '<div class="navigation pagination">' + nav_obj.top_back_button + flp_button + nav_obj.top_continue_button + '</div>'
            LOG('createNavigationButtons : ', INFO, 'Completes')
        except Exception, e:
            self.exception_list.append(str(obj.short_page_title) + ": " + str(e))
            LOG('createNavigationButtons : ', INFO, str(obj.short_page_title) + ": " + str(e))            
        return top_nav_buttons, nav_obj.bottom_nav_buttons

    
                
    def getPulledContent(self, pulled_file, course, git_url, is_studio_course):
        ''' Function to get the list of Pulled files'''
       
        LOG('Updating the Course: ', INFO, 'Started')
        
        updated_section_list = []        
        parent_child_mapping_list = []  # list of dictionary used to map parent and child in the course.xml    
        try:
            section_updated = []
            pulled_file_list = pulled_file.split("\n")       # fetching the list of Files from pulling.txt
            soup = BeautifulSoup(open(self.course_file_path))
               
            for sequential in soup.findAll('sequential', {'visible_to_staff_only': None}):  #code to create the list of dictionary used to map files in course.xml           
                vertical_tag_list = sequential.findAll('vertical', {'visible_to_staff_only': None})
                
                for vertical in vertical_tag_list:
                    parent_child_dict = {}
                    html_prob_id_list = []
                    
                    for html_prob in vertical.findAll(['html', 'problem', 'video'], {'visible_to_staff_only': None}):                
                        tag = html_prob.name
                                      
                        if tag == 'problem': html_prob_id_list.append(tag + '/' + html_prob.get('url_name') + '.xml') 
                                                
                        elif tag == 'html':  html_prob_id_list.append(tag + '/' + html_prob.get('filename') + '.html')
                        
                        else: html_prob_id_list.append(tag + '/' + createId(html_prob.get('url_name')))
                        
                    if vertical_tag_list.index(vertical) > 0:   parent_child_dict['parent'] = vertical.get('url_name')
                       
                    else: parent_child_dict['parent'] = sequential.get('url_name') 
                                   
                    parent_child_dict['files'] = html_prob_id_list
                    parent_child_mapping_list.append(parent_child_dict)
                    
            for pulled_file in pulled_file_list:                
                for dict in parent_child_mapping_list:
                    files_list = [file for file in dict['files'] if file == pulled_file]
                    
                    if files_list: 
                        section_obj_list = getSectionObject(self.portal_catalog, createId(dict['parent']), self.course_url)
                        
                        if section_obj_list :                            
                            for section_obj in section_obj_list :
                                flag = False
                                flp_body_text = '' 
                                section_path = '/' + section_obj.virtual_url_path()
                                                               
                                top_nav_text, bottom_nav_text = self.createNavigationButtons(section_obj)
                               
                                for file in dict['files']:                                 
                                   flp_file = self.cloned_dir_path + '/' + file
                                   flp_soup = ''
                                   
                                   if file.split('/')[0] == 'video':
                                        path = "/".join(section_obj.getPhysicalPath())
                                        media_ResourceObj = getMediaResourceObject(self.portal_catalog, file.split('/')[1], path)
                                        if media_ResourceObj:
                                            flp_body_text += '<h2 class="subhead">' + media_ResourceObj.title + '</h2>' + \
                                                             '<p>' + media_ResourceObj.inline_embed_id + '</p>'
                                            section_obj.has_inline_embed = True
                                   
                                   else:
                                       if file.split('/')[0] == 'problem':  
                                           flp_soup = BeautifulSoup(getModifiedAssessmentString(self, flp_file, flag))
                                           flag = True
                                       else: flp_soup = BeautifulStoneSoup(open(flp_file)) 
                                       
                                       flp_soup = addResourcesFromBackend(section_obj, self.context, self.portal_catalog, self.cloned_dir_path, flp_soup)
                                       flp_soup = self.modifyHtmlContent(section_obj, flp_soup, section_path)
                                       flp_body_text += str(flp_soup)
                                   
                                section_obj.setText(top_nav_text + flp_body_text + bottom_nav_text)
                                section_obj.reindexObject()
                                
                                updated_section_list.append(section_obj.short_page_title)
                                section_updated.append(pulled_file)
                                   
               # Message Displayed to user
            unused_files = set(pulled_file_list) - set(section_updated)               
            message = 'Section Updated:' + str(updated_section_list)
            
            if unused_files :
               message += '\n No Section updated for following files : ' + str(unused_files)
                         
            os.remove(PULLED_FILE_PATH)
            LOG('Updating the Course: ', INFO, 'Completed')       
            return message
        
        except Exception, e:
            self.exception_list.append(str(e))
            LOG('getPulledContent : ', INFO, str(e)) 
            return self.exception_list
        
class navigation:
    ''' Class to create navigation Buttons'''
    
    def __init__(self, obj, pulling, chap_seq_vert_tag_list=None, id_obj_dict=None):
        self.back_button = ''
        self.continue_button = ''
        self.top_back_button = ''
        self.top_continue_button = ''
        self.bottom_nav_buttons = ''
        self.chap_seq_vert_tag_list = chap_seq_vert_tag_list
        self.pulling = pulling
        self.id_obj_dict = id_obj_dict
        self.createBackContinueButtons(obj)       

    def createBackContinueButtons(self, obj):
        '''Function to create the Back and Continue buttons using previous and next url ''' 
        
        LOG('createBackContinueButtons : ', INFO, 'started')        
        top_back_btn_id = 'id="top_bck_btn"'
        top_continue_btn_id = 'id="top_continue_btn"'
        bottom_back_btn_id = 'id="bck_btn"'
        bottom_continue_btn_id = 'id="continue_btn"'
        
        try:
            if self.pulling == True:
                body_text = obj.getText()
                soup = BeautifulSoup(body_text)
                 
                for top_back_text in soup.findAll('li', id="top_bck_btn"):
                    self.top_back_button = str(top_back_text) + ' '
                    
                for top_continue_text in soup.findAll('li', id="top_continue_btn"):
                    self.top_continue_button = str(top_continue_text)
                
                for bottom_back_text in soup.findAll('button', id="bck_btn"):
                    self.back_button = str(bottom_back_text) + ' '
                    
                for bottom_continue_text in soup.findAll('button', id="continue_btn"):
                    self.continue_button = str(bottom_continue_text) 
               
            else:                
                previous_url, previous_title = self.createPreviousUrl(obj)
                
                next_url, next_title = self.createNextUrlforFlp(obj)
                
                if next_url != '' and previous_url != '':   # check to remove the next button from last FLP
                    self.back_button = BACK_BUTTON % (bottom_back_btn_id, previous_url, previous_title)       
                    self.top_back_button = BACK_LI_TAG % (top_back_btn_id, previous_url, previous_title)                     
                    self.continue_button = CONTINUE_BUTTON % (bottom_continue_btn_id, next_url, next_title) 
                    self.top_continue_button = CONTINUE_LI_TAG % (top_continue_btn_id, next_url, next_title)
                    
                elif next_url == '':
                    self.back_button = BACK_BUTTON % (bottom_back_btn_id, previous_url, previous_title)
                    self.top_back_button = BACK_LI_TAG % (top_back_btn_id, previous_url, previous_title) 
                     
                else :
                    self.continue_button = CONTINUE_BUTTON % (bottom_continue_btn_id, next_url, next_title)
                    self.top_continue_button = CONTINUE_LI_TAG % (top_continue_btn_id, next_url, next_title)                    
                
            self.bottom_nav_buttons = '<div class="navigation progress">' + self.back_button + self.continue_button + '</div>'    # Adding the CSS to bottom Navigation buttons
            
        except Exception, e:
            LOG('createBackContinueButtons : ', INFO, str(obj.short_page_title) + ": " + str(e))            
        return
 
    def createNextUrlforFlp(self, obj):
        '''Function to create the url of next FLP '''
         
        LOG('createNextUrlforFlp : ', INFO, 'started')  
        path = obj.virtual_url_path()
        count = 0
        next_id = '' 
        url = ''         
        try:     
            for tag_dict in self.chap_seq_vert_tag_list:         
                key, tag = tag_dict.items()[0]        
                if (obj.id == key):     # checking if the key is similar to current section ID 
                                        
                    if count == (len(self.chap_seq_vert_tag_list) - 1): return '', ''   # check to set the previous url of First Section
                    
                    # Check to find the previous of the first FLP created.(specifically done for USERFLOW change))
                    elif tag[0] in ('vertical', 'chapter'):   next_id, next_tag = self.chap_seq_vert_tag_list[count + 1].items()[0]  
                   
                    else:
                        if (count + 2) <= (len(self.chap_seq_vert_tag_list) - 1): 
                            next_id, next_tag = self.chap_seq_vert_tag_list[count + 2].items()[0]                            
                        else : return '', ''
                        
                    # condition to set the next url on the basis of its tag 
                    if tag[0] == 'sequential':
                        if next_tag[0] == 'sequential': url = '/'.join(path.split('/')[:-1])
                        elif next_tag[0] == 'chapter': url = '/'.join(path.split('/')[:-2])
                        else : url = path 
                    
                    elif tag[0] == 'vertical':
                        if next_tag[0] == 'vertical': url = '/'.join(path.split('/')[:-1])
                        elif next_tag[0] == 'sequential': url = '/'.join(path.split('/')[:-2])
                        elif next_tag[0] == 'chapter': url = '/'.join(path.split('/')[:-3])
                                          
                    else : url = path                                   
                   
                    return '/' + url + '/' + createId(next_id), next_tag[1]
                
                count += 1
        except Exception, e:
            LOG('createNextUrlforFlp : ', INFO, str(obj.short_page_title) + ": " + str(e))
        return
                         
    def createPreviousUrl(self, obj):
        '''Function to create the url of Previous FLP '''
         
        LOG('createPreviousUrl : ', INFO, 'started')
        count = 0
        previous_id = ''  
        try:         
            for tag_dict in self.chap_seq_vert_tag_list:          
                key, tag = tag_dict.items()[0]
                      
                if (obj.id == key):     # checking if the key is similar to current section ID       
                    if count == 0:  return '', ''    # check to set the previous url of First Section
                    
                    elif self.chap_seq_vert_tag_list[count - 2].values()[0][0] == 'sequential' :    # Check to find the previous of the first FLP created.(specifically done for USERFLOW change))                               
                        previous_id, previous_tup = self.chap_seq_vert_tag_list[count - 2].items()[0]
                        
                    else:   previous_id, previous_tup = self.chap_seq_vert_tag_list[count - 1].items()[0]
                         
                    if previous_id in self.id_obj_dict.keys():
                        previous_obj = self.id_obj_dict[previous_id]             
                        return '/' + previous_obj.virtual_url_path(), previous_tup[1]
                    
                count += 1
                
        except Exception, e:
                      LOG('createPreviousUrl : ', INFO, str(obj.short_page_title) + ": " + str(e))
        return 
        
