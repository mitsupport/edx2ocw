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
from ocw.publishing.browser.edxcourseconversion.studioEdxCourseConversion import \
    StudioEdxCourseConversion
from ocw.publishing.browser.edxcourseconversion.utils import *
from zLOG import LOG, INFO, DEBUG
import os
import re
import string
import zope.event


class EdxCourseConversion(BrowserView):
    template = ViewPageTemplateFile('edx_cms_course_conversion.pt')
    __call__ = template  
   
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.portal_catalog = getToolByName(self.context, 'portal_catalog')
        self.exception_list = []
        self.problem_count = 0;
        self.solution_count = 0;
        self.problem_btns_count = 1;
        
    def getCourseUrl(self):
        '''function to get the Course URL provided as input to the user'''
        try:
            self.course = self.request.get('course_url', '')     # getting the Input value from the User
            git_url = self.request.get('git_url', '')       # getting the Input value from the User
            is_studio_course = self.request.get('is_studio_course', '')
            
            self.pulling = os.path.isfile(PULLED_FILE_PATH)              
            if is_studio_course == 'on':
                course_url, cloned_dir_path = getCourseDetails(self.course, git_url)             
                StudioEdxCourse = StudioEdxCourseConversion(self.context, self.request, course_url, cloned_dir_path)
                if self.pulling == True :
                    file = open(PULLED_FILE_PATH, "r").read()      
                    if os.path.getsize(PULLED_FILE_PATH) > 0:
                       return StudioEdxCourse.getPulledContent(file, self.course, git_url, is_studio_course)
                    else:
                        os.remove(PULLED_FILE_PATH) 
                        return 'Nothing to be updated'
                else : 
                     return StudioEdxCourse.createListofTagDictionary()
            else : 
                self.course_URL = '/Plone' + self.course             # creating the Course Url
                cloned_dir = string.replace(git_url.split('/')[1], '.git', '')    
                self.cloned_dir_path = CLONED_COURSE_PATH + '/' + cloned_dir      # creating the Cloned Course Directory Path
                #  checking if Pulling or Cloning needs to done    
                if self.pulling == True :
                    file = open(PULLED_FILE_PATH, "r").read()      
                    if os.path.getsize(PULLED_FILE_PATH) > 0:
                       return self.getPulledContent(file)       # if Pulled text file exist Pulling will be done
                    else: return 'Nothing to be updated'
                else : return self.getFileContents()  
        except Exception, e:
               self.exception_list.append(str(e))
               LOG('Exceptions : ', INFO, "Exception:" + str(e))  
    
    def getCourseDirectory(self):
        '''function to get the Course Directory which is cloned/Pulled from Github'''
        
        # Accessing the Cloned Course Structure to fetch Files
        try:
            courseXml = BeautifulSoup(open(self.cloned_dir_path + '/course.xml'))      
            course_name = courseXml.find('course')
            self.courseFileName = course_name.get('url_name')
            self.courseName = course_name.get('course')
            self.courseOrg = course_name.get('org')
            self.courseUrl = '/courses/' + self.courseOrg + '/' + self.courseName + '/' + self.courseFileName
            # Code to create list of directory of tag and its url_name, this list will be used in both : create and update of course
            self.tag_list = []       
            soup = BeautifulSoup(open(self.cloned_dir_path + '/course/' + self.courseFileName + '.xml'))
            for tag in soup.findAll():
                if tag.get('url_name') != None:     # Check to remove the tags like <course> where there is no url_name attribute
                   self.tag_list.append({createId(tag.get('url_name')):(tag.name, tag.get('display_name'))})
                           
        except Exception, e:
               self.exception_list.append(str(e))
               LOG('Exceptions : ', INFO, "Exception:" + str(e))         
        return 
    
    def isSectionExist(self, section_id):
        '''function to find if the section exist and returns the list of section objects'''
      
        section_obj_list = []
        sections = self.portal_catalog.searchResults({'meta_type' : 'CourseSection'}, path={'query': self.course_URL, 'depth': 5 }, getId=str(section_id))        
        if sections:
           try:
               for section in sections:
                   section_obj_list.append(section.getObject())
           except Exception, e:
               self.exception_list.append(str(section_id) + ": " + str(e))
               LOG('Exceptions : ', INFO, str(section_id) + ": " + str(e))      
        return section_obj_list
        
    def getPulledContent(self, file_list):
       ''' Function to get the list of Pulled files'''
       
       LOG('Updating the Course: ', INFO, 'Started')          
       modified_file_list = []   
       self.section_title_list = []
       modified_files_urls_list = file_list.split("\n")       # fetching the list of Files from pulling.txt
       file_name = ''
       # fetching the list of Files which are either created or Deleted
       try:
           for modified_file_url in modified_files_urls_list:
               if "/" in modified_file_url: 
                   modified_file = modified_file_url.split('/')
                   self.file_tag = modified_file[0]
                   file_name = str(modified_file[1])
                   if file_name == 'moindex.html':
                       section_obj_list = self.isSectionExist('measurable-outcome-index')
                       if section_obj_list:
                           self.modifyMoIndexForPulling(section_obj_list[0], file_name) 
                           modified_file_list.append(modified_file_url)                     
                   else:
                        LOG('file_name : ', INFO, file_name)
                        flp_name = file_name.replace('.xml', '').strip()
                        section_id = createId(flp_name)
                        section_obj_list = self.isSectionExist(section_id)
                        self.getCourseDirectory()    # This function is used to get the Course Directory which is cloned/Pulled from Github                               
                        for tag_dict in self.tag_list:                    
                             id, tag = tag_dict.items()[0]
                             if id == section_id and tag[0] == self.file_tag:
                                 if not section_obj_list:     #This condition is used to handle update of TLP section contents         
                                     section_id, section_tag = self.tag_list[self.tag_list.index(tag_dict) - 1].items()[0]
                                     if section_tag[0] == "sequential":
                                         self.updateSections(self.isSectionExist(section_id), file_name)                  
                                 else: self.updateSections(section_obj_list, file_name)
                                 modified_file_list.append(modified_file_url)
              
           # Message Displayed to user
           list_of_unused_files = set(modified_files_urls_list) - set(modified_file_list)               
           message = 'Section Updated:' + str(self.section_title_list)
           if list_of_unused_files :
               message += '\n No Section updated for following files : ' + str(list(list_of_unused_files))          
           os.remove(PULLED_FILE_PATH)
           LOG('Updating the Course: ', INFO, 'Completed')
           return message
       except Exception, e:
            self.exception_list.append(str(e)) 
            LOG('Exceptions : ', INFO, "Exception:" + str(e))        
            return str(e)
    
    def modifyMoIndexForPulling(self, section_obj, file_name):
        ''' Function to updated the contents of MOIdex section using Pulled file'''
        try: 
            mo_link_text_dict = {}
            body_text = section_obj.getText()
            soup = BeautifulSoup(body_text)
            course_url = "/" + section_obj.getMasterPage().virtual_url_path()
            for tag in soup.findAll('a', {"href" : re.compile(course_url)}):   # this creates a dictionary to  retain the old links             
                mo_link_text_dict[str(' '.join(tag.contents[0].split(' ')[1:]))] = (str(tag['href']), str(tag.contents[0]))
                
            flp_file = self.cloned_dir_path + '/' + self.file_tag + '/' + file_name
            updated_mo_content = BeautifulSoup(open(flp_file)) 
            for updated_tag in updated_mo_content.findAll('a', {"href" : re.compile("/jump_to_id/") }):
                tag_text = updated_tag.contents[0]
                if tag_text in mo_link_text_dict:
                    updated_tag['href'] = mo_link_text_dict[tag_text][0]
                    updated_tag.contents[0].replaceWith(mo_link_text_dict[tag_text][1]) 
                else:
                  section_id = createId(updated_tag.get('href').split('/')[-1])
                  section_obj_list = self.isSectionExist(section_id)
                  if not section_obj_list:     #This condition is used to handle the links of TLP sections         
                     for tag_dict in self.tag_list:                    
                         id = tag_dict.keys()[0]
                         if id == section_id:       
                             section_id, section_tag = self.tag_list[self.tag_list.index(tag_dict) - 1].items()[0]                            
                             if section_tag[0] == "sequential":
                                 section_obj_list = self.isSectionExist(section_id)
                  if section_obj_list:
                      short_page_title = section_obj_list[0].short_page_title
                      updated_tag['href'] = '/' + section_obj_list[0].virtual_url_path()     
                      flp_numbering = short_page_title.split(' ')[0]
                      if flp_numbering.count('.') < 2:
                          flp_numbering = flp_numbering + '.1'
                      updated_tag.contents[0].replaceWith(flp_numbering + ' ' + str(tag_text))
                      
            tr_tags = updated_mo_content.findAll('tr')  # Aligning all the MO tags to left
            for tr_tag in tr_tags:
                 tr_tag['align'] = 'left'
                                    
            section_obj.setText(str(updated_mo_content))                                        
            section_obj.reindexObject()
            self.section_title_list.append(section_obj.short_page_title)
        except Exception, e:
            self.exception_list.append(str(section_obj.short_page_title) + ": " + str(e)) 
            LOG('Exceptions : ', INFO, str(section_obj.short_page_title) + ": " + str(e))               
        
    def updateSections(self, section_obj_list, file_name): 
        ''' Function to updated the contents of TLP\FLp sections using the list of Pulled files'''
        try:
            for section_obj in section_obj_list :
               self.section_title_list.append(section_obj.short_page_title)           
               section_path = '/' + section_obj.virtual_url_path()
               flp_file = self.cloned_dir_path + '/' + self.file_tag + '/' + file_name
               if self.file_tag == 'problem':
                   flp_soup = BeautifulSoup(getModifiedAssessmentString(self, flp_file))
               else:
                   flp_soup = BeautifulStoneSoup(open(flp_file)) 
               
               self.addImage(section_obj, flp_soup)                         
               self.moindex_path = self.course + '/' + 'measurable-outcome-index'
               flp_soup = self.modifyInterSectionLinksForPulling(section_obj, flp_soup)
               self.modifyHtmlContent(section_obj, flp_soup, section_path)
        except Exception, e:
            self.exception_list.append(str(section_obj.short_page_title) + ": " + str(e)) 
            LOG('Exceptions : ', INFO, str(section_obj.short_page_title) + ": " + str(e))  
        
    def modifyInterSectionLinksForPulling(self, obj, content):
        ''' Function to modify the internal section links'''
        
        section_link_list = content.findAll('a', target="_blank")       
        if section_link_list:
           try:
               section_id = []
               # finding all Internal Section links
               for section_link in section_link_list:
                   section_link_text = str(section_link.string).strip()
                   if (section_link_text.count('.') == 2) and ((self.courseUrl + '/courseware/') in str(section_link)):                        
                       section_link_url = str(section_link).split('/courseware/')[1]
                       section = str(section_link_url).split("/")[0:3]
                       for sect in section:
                           section_id.append(createId(sect)) 
                       section_url = self.course_URL + '/' + section_id[0] + '/' + section_id[1]
                       section_url = string.replace(section_url, "_", '-')
                       # searching if the section exists and getting its object
                       sections = self.portal_catalog.searchResults({'meta_type' : 'CourseSection'}, path={'query': section_url, 'depth': 5 , 'sort_on': 'getObjPositionInParent'})                   
                       if sections:
                           counter = int(section_id[2])                     
                           section_link_obj = sections[counter].getObject()
                           section_link_path = '/' + section_link_obj.virtual_url_path()
                           section_link['href'] = section_link_path                  # modifying the content after changing the internal section links
           except Exception, e:
                self.exception_list.append(str(obj.short_page_title) + ": " + str(e))   
                LOG('Exceptions : ', INFO, str(obj.short_page_title) + ": " + str(e))   
        return content
        
    def modifyInterSectionLinks(self, obj, content):
        ''' Function to modify the internal section links'''
        
        if content != '':
            section_link_list = content.findAll('a', target="_blank")   # finding all Internal Section links
            if section_link_list:
               try:
                   for section_link in section_link_list:
                       section_link_text = str(section_link.string).strip()
                       if (section_link_text.count('.') == 2) and ((self.courseUrl + '/courseware/') in str(section_link)):
                            if section_link_text in self.flp_links_dict:                            # searching for the section link text in dictionary keys
                                section_link['href'] = self.flp_links_dict[section_link_text]       # modifying the content after changing the internal section links
                            elif obj not in self.unmodified_section_links_list :
                                self.unmodified_section_links_list.append(obj)
               except Exception, e:
                    self.exception_list.append(str(obj.short_page_title) + ": " + str(e)) 
                    LOG('Exceptions : ', INFO, str(obj.short_page_title) + ": " + str(e)) 
        return content
    
    def modifyRemainingInterSectionLinks(self):
        ''' Function to modify the internal section links'''
        
        for obj in self.unmodified_section_links_list:
            try:
                section_text = obj.getText()
                section_content = BeautifulSoup(section_text) 
                content = self.modifyInterSectionLinks(obj, section_content)
                obj.setText(str(content))                                        
                obj.reindexObject()
            except Exception, e:
                self.exception_list.append(str(obj.short_page_title) + ": " + str(e))
                LOG('Exceptions : ', INFO, str(obj.short_page_title) + ": " + str(e)) 
                        
    def modifyMoIndexContent(self, content, flp_path):
        '''function to modify and set the content of the MO Index section '''
              
        link = '/jump_to_id/' + self.flp
        try:
            for tag in content.findAll('a'):
                href = tag.get('href') 
                if link == str(href):
                    tag['href'] = flp_path
                    tag_text = tag.contents[0]
                    tag.contents[0].replaceWith(self.flp_numbering + ' ' + str(tag_text))
        except Exception, e:
           self.exception_list.append(str(self.flp) + ": " + str(e))
           LOG('Exceptions : ', INFO, str(self.flp) + ": " + str(e)) 
        return content
    
    def modifyHtmlContent(self, obj, content, path):
        '''function to modify and set the content of the section '''   
        
        try:
            top_nav_text, bottom_nav_text = self.createNavigationButtons(obj) 
            body_text = top_nav_text
            if content != '':
                content = re.sub(r'<html.*', "", str(content))     
                btag_textlist = re.findall('<p>\n<b class="bfseries">(.*)</b>\n</p>', content)  
                if btag_textlist:
                  for text in btag_textlist:    
                      content = string.replace(content, '<p>\n<b class="bfseries">' + text + '</b>\n</p>', '<h2 class="subhead">' + text + '</h2>')
                for key, value in TAG_REPLACEMENTS.iteritems():
                    if key in content:
                        content = string.replace(content, key, value)
                        if key in ('[mathjaxinline]', '[mathjax]'):
                            obj.is_mathml_document = True
                mo_link = self.courseUrl + '/moindex'
                if mo_link in content:      # To replace the links of MO buttons appearing on each page
                    content = string.replace(content, mo_link, self.moindex_path)
                
                if '/static/html' in content:                # Replacing the links of images to make it point to CMS Path
                    content = string.replace(content, '/static/html', path) 
            body_text += str(content)
            body_text += bottom_nav_text
            obj.setText(str(body_text))                                        
            obj.reindexObject()
            LOG('FLP Created : ', INFO, str(obj.short_page_title))
        except Exception, e:
                self.exception_list.append(str(obj.short_page_title) + ": " + str(e))
                LOG('Exceptions : ', INFO, str(obj.short_page_title) + ": " + str(e))       
        return
    
    def createNavigationButtons(self, obj):
        btn_counter = 1
        flp_button = ''
        count = 0
        btn_class = ''
        top_nav_buttons = ''
        
        try:
            if self.pulling == True :
                nav_obj = navigation(obj, self.pulling, self.tag_list, self.exception_list)           
                body_text = obj.getText()
                soup = BeautifulSoup(body_text)
                for  btn in soup.findAll('li', {"id" : re.compile('flp_btn_') }):
                     flp_button += str(btn) + ' '
            else: 
                nav_obj = navigation(obj, self.pulling, self.tag_list, self.exception_list, self.id_obj_dict, self.next_count_list, self.previous_count_list)               
                url = '/' + obj.virtual_url_path()               
                for tag_dict in self.tag_list:
                    try:
                      key, tag = tag_dict.items()[0] 
                      if (obj.id == key) and (count not in self.flp_count_list):  # check to match the key with the current FLP Id                                 
                          self.flp_count_list.append(count)
                          if tag[0] in ('html', 'problem'):                           
                              url = '/'.join(url.split('/')[:-1])
                              break
                      count += 1
                    except Exception, e:
                          self.exception_list.append(str(obj.short_page_title) + ": " + str(e))
                            
                while btn_counter <= len(self.html_problem_tag_list):
                   btn_text = str(self.counter) + '.' + str(self.tlp_counter) + '.' + str(btn_counter)
                   if self.flp_numbering == btn_text: btn_class = 'class="button_selected"'
                   else : btn_class = ''
                   btn_url = ''
                   btn_title = self.html_problem_tag_list[btn_counter - 1].get('display_name')
                   if btn_counter == 1:
                       btn_url = url
                   else:
                        btn_url = url + '/' + createId(self.html_problem_tag_list[btn_counter - 1].get('url_name')) 
                   flp_button_id = 'flp_btn_' + str(btn_counter)            
                   flp_button += FLP_BUTTON_TAG % (flp_button_id, btn_class, btn_url, btn_text, btn_title)
                   btn_counter += 1                       
            
            top_nav_buttons = '<div class="navigation pagination">' + nav_obj.top_back_button + flp_button + nav_obj.top_continue_button + '</div>'
        except Exception, e:
                    self.exception_list.append(str(obj.short_page_title) + ": " + str(e))
                    LOG('Exceptions : ', INFO, str(obj.short_page_title) + ": " + str(e))
        return top_nav_buttons, nav_obj.bottom_nav_buttons
         
   
    
    def createFlp(self, tag , tlp_obj, course_obj):
        ''' Creation of Fourth Level Pages'''
        
        try:
            self.flp = tag.get('url_name')      # url_name is used to create the Section Id and to fetch he respective .xml file
            self.flp_numbering = str(self.counter) + '.' + str(self.tlp_counter) + '.' + str(self.flp_counter) # To append the section no. to the section title
            updated_flp = self.flp_numbering + ' ' + tag.get('display_name')   # 'disply_name' attribute is used only to create the title
            flp_id = createId(self.flp)
            flp_file = self.cloned_dir_path + '/' + tag.name + '/' + self.flp + '.xml'   # Fetching the XML File related to the the FLP
            flp_soup = ''
            if os.path.isfile(flp_file):
                if tag.name == 'problem':
                    flp_soup = BeautifulSoup(getModifiedAssessmentString(self, flp_file))                    
                else:
                    flp_soup = BeautifulStoneSoup(open(flp_file)) 
            if self.html_problem_tag_list.index(tag) > 0:
                self.createSectionFromBackend(flp_id, self.tlp_title, tlp_obj, course_obj, updated_flp)            
                flp_obj = getattr(tlp_obj, flp_id)                                                 
                flp_obj.unmarkCreationFlag()
                zope.event.notify(ObjectInitializedEvent(flp_obj))
                flp_obj.always_publish = True,
                                
                self.id_obj_dict[flp_id] = flp_obj
                obj = flp_obj                
               
            else :
                obj = tlp_obj
                
            flp_path = '/' + obj.virtual_url_path()   
            self.all_flps_list.append({updated_flp:obj}) # list of all FLP object under one TLP/Sequential tags)
            self.flp_links_dict[self.flp_numbering] = flp_path  # dictionary of FLP Numbering : Flp Path used to set the Internal Section Links
            
            self.addImage(obj, flp_soup)        
            flp_soup = self.modifyInterSectionLinks(obj, flp_soup)
            self.modifyHtmlContent(obj, flp_soup, flp_path)
                       
            self.moindex_content = self.modifyMoIndexContent(self.moindex_content, flp_path)
        except Exception, e:
            self.exception_list.append(str(tlp_obj.short_page_title) + ": " + str(e))
            LOG('Exceptions : ', INFO, str(tlp_obj.short_page_title) + ": " + str(e))
        return    
   
    def addImage(self, obj, content):
        ''' Function to add Images from the backend '''
                
        created_image_list = []
        if content != '':
            image = content.findAll('img')      # List of all img tags in the Xml File
            figure_link_list = content.findAll('a')     # List of all <a> tags in the Xml File
            for link in figure_link_list:
                if '/static/html' in str(link):
                    image.append(link)
            for img in image:
               try:
                 if img.name == 'img': location = img.get('src')                     
                 else: location = img.get('href')
                 imagename = location.split("/")[3]
                 img_path = (self.cloned_dir_path + location).encode('utf-8')
                 if (imagename not in created_image_list) and (os.path.isfile(img_path)) : # Check to fix the figure links with images from different section 
                    image_obj = open(img_path, "rb")  
                    if self.pulling == True:
                        path = "/".join(obj.getPhysicalPath())
                        image_list = self.portal_catalog.searchResults({'meta_type' : 'OCWImage'}, path={'query': path  , 'depth': 1}, getId=imagename) 
                        created_image_list.append(imagename)
                        if not image_list:   
                           self.createImageFromBackend(obj, imagename, image_obj)
                           created_image_list.append(imagename)
                    else:
                        self.createImageFromBackend(obj, imagename, image_obj)
                        created_image_list.append(imagename)
               except Exception, e:
                    self.exception_list.append(str(obj.short_page_title) + ": " + str(e))
                    LOG('Exceptions : ', INFO, str(obj.short_page_title) + ": " + str(e))       
        else: 
            self.exception_list.append('No Content found for the section : ' + str(obj.short_page_title))
            LOG('No Content found for the section : ', INFO, str(obj.short_page_title))
        return    
  
    def addSubsequentialLinksOnSectionPages(self, tlp_obj, list):
        ''' function to add links of TLPs and FLPs in parent level '''
       
        body_text = '' 
        try:
            body_text = '<p><strong>' + tlp_obj.title + '</strong></p>'     # link of TLP   
            body_text += '<ul class="arrow">'                                               # list of link of FLP related to the TLP  
            for obj_dict in list:
                title, obj = obj_dict.items()[0]  
                body_text += '<li><a href="/' + obj.virtual_url_path() + '">' + title + '</a></li>'        
            body_text += '</ul>'      
              
        except Exception, e:
           self.exception_list.append(str(tlp_obj.title) + ": " + str(e))
           LOG('Exceptions : ', INFO, str(tlp_obj.title) + ": " + str(e))       
        return  body_text   
    
    def setBodyTextOnSectionPages(self, first_tlp_obj, section_obj):
        ''' function to set the body text of section pages to display list of TLPs and FlPs links '''
        try:           
            nav_obj = navigation(section_obj, self.pulling, self.tag_list, self.exception_list, self.id_obj_dict, self.next_count_list, self.previous_count_list)
            top_nav_text = '<div class="navigation progress">' + nav_obj.back_button + nav_obj.continue_button + '</div>'
            body_text = top_nav_text + str(self.tlp_text) + nav_obj.bottom_nav_buttons
            section_obj.setText(str(body_text))
            section_obj.reindexObject() 
        except Exception, e:
           self.exception_list.append(str(section_obj.title) + ": " + str(e))
           LOG('Exceptions : ', INFO, str(section_obj.title) + ": " + str(e)) 
        return
        
    def createSectionFromBackend(self, id, title, obj, parent, short_page_title=None):
        ''' Function to create Sections from the backend '''
        
        try: 
            if short_page_title == None: short_page_title = title       # to set the FLP Title in the bread crumb
            obj.invokeFactory(type_name='CourseSection',
                                     id=id,
                                     title=title,
                                     short_page_title=short_page_title,
                                     parent_module=parent,
                                             )
        except Exception, e:
           self.exception_list.append(str(short_page_title) + ": " + str(e))
           LOG('Exceptions : ', INFO, str(short_page_title) + ": " + str(e)) 
        return  
     
    def createImageFromBackend(self, obj, imagename, image_obj):
         ''' Function to create Image from the backend '''
        
         try: 
             obj.invokeFactory(type_name='OCWImage',
                                                         id=imagename,
                                                         title=imagename,
                                                         image=image_obj,
                                                         excludeFromNav=True,
                                                         description='New image Upload',
                                                         always_publish=True
                                                    )
             ocw_ImageObj = getattr(obj, imagename)
                                 
             portal_membership = getToolByName(self.context, 'portal_membership')   
             if not portal_membership.isAnonymousUser():
                 member = portal_membership.getAuthenticatedMember()
                 ocw_ImageObj.changeOwnership(member.getUser(), 1)
             ocw_ImageObj.unmarkCreationFlag()                    
             zope.event.notify(ObjectInitializedEvent(ocw_ImageObj))
         except Exception, e:
           self.exception_list.append(str(obj.short_page_title) + ": " + str(e))
           LOG('Exceptions : ', INFO, str(obj.short_page_title) + ": " + str(e))
         return   
   
    def getFileContents(self):
        ''' Function to read the contents from the Edx Course structure and creation of sections accordingly '''
                       
        course = self.portal_catalog.searchResults({'meta_type':('Course', 'SupplementalResource') },
                                                   path={'query': self.course_URL })     # Catalog search to find the course object
        try:
            if len(course) == 1:
                course_obj = course[0].getObject()
                
                if (os.path.isdir(self.cloned_dir_path) == True):                       
                    moindex_title = 'Measurable Outcome Index'
                    moindex_id = createId(moindex_title)
                    self.createSectionFromBackend(moindex_id, moindex_title, course_obj, course_obj)    # code to create the Measurable Outcomes Index section in course
                    
                    moindex_obj = getattr(course_obj, moindex_id)               
                    moindex_obj.unmarkCreationFlag()
                    zope.event.notify(ObjectInitializedEvent(moindex_obj))
                    self.moindex_path = '/' + moindex_obj.virtual_url_path()
                    
                    moindexXml = BeautifulSoup(open(self.cloned_dir_path + '/tabs/moindex.html'))     # Reading the contents of MO Index section                    
                    tr_tags = moindexXml.findAll('tr')
                    for tr_tag in tr_tags:
                         tr_tag['align'] = 'left'            # modifying the content of Measurable Outcomes section
                    self.moindex_content = moindexXml                 
                    
                    # Reading the contents of Course.xml to create the Sections,TLP and Flps
                    self.getCourseDirectory() 
                    soup = BeautifulSoup(open(self.cloned_dir_path + '/course/' + self.courseFileName + '.xml'))   
                   
                    self.counter = -1   
                    self.id_obj_dict = {}                    # dictionary of Section Id and its object to create the previous url of section                                 
                    self.flp_links_dict = {}                 # dictionary of FLP numbers and their path 
                    self.unmodified_section_links_list = []          # dictionary of section links which are not created till modification                    
                    self.previous_count_list = []
                    self.next_count_list = []
                    self.flp_count_list = []
                    for chapter in soup.findAll('chapter'):          # list of all chapter tags will be used to create  course section
                        self.counter += 1                            # counter of section used to in the creation of title
                        section = chapter.get('url_name') 
                        section_id = createId(section)
                        section_title = str(self.counter) + ' ' + chapter.get('display_name')
                        self.createSectionFromBackend(section_id, section_title, course_obj, course_obj)                      
                        
                        section_obj = getattr(course_obj, section_id)                   
                        section_obj.unmarkCreationFlag()
                        zope.event.notify(ObjectInitializedEvent(section_obj))
                        self.id_obj_dict[section_id] = section_obj                        
                     
                        self.tlp_counter = 0
                        self.tlp_text = ''
                        for sequential in chapter.findAll('sequential'):    # list of all sequential tags inside each chapter tag will be used to create TLP
                            self.tlp_counter += 1                                # counter of TLP used to in the creation of title
                            tlp = sequential.get('url_name')  
                            tlp_id = createId(tlp)
                            self.tlp_title = str(self.counter) + '.' + str(self.tlp_counter) + ' ' + sequential.get('display_name')
                            self.createSectionFromBackend(tlp_id, self.tlp_title, section_obj, course_obj)                            
                            
                            tlp_obj = getattr(section_obj, tlp_id)
                            tlp_obj.unmarkCreationFlag()
                            zope.event.notify(ObjectInitializedEvent(tlp_obj))
                            if self.tlp_counter == 1: first_tlp_obj = tlp_obj
                            tlp_obj.list_in_left_nav = True
                            self.id_obj_dict[tlp_id] = tlp_obj
                            
                            self.all_flps_list = []
                            self.flp_counter = 0   
                            self.html_problem_tag_list = sequential.findAll(['html', 'problem']) # list of all html/Problem tags inside each sequential tag will be used to create FLP
                            for tag in self.html_problem_tag_list:       
                                self.flp_counter += 1                         # counter of FLP used to in the creation of title
                                self.createFlp(tag, tlp_obj, course_obj) 
                            
                            self.tlp_text += self.addSubsequentialLinksOnSectionPages(tlp_obj, self.all_flps_list)    # code to create the links of sequential and sub-sequential
                            
                        self.setBodyTextOnSectionPages(first_tlp_obj, section_obj)
                                                               
                    # Modifying the remaining Internal section links
                    if self.unmodified_section_links_list:
                        self.modifyRemainingInterSectionLinks()
                        
                  # setting the body text of MO Index Section after all the modifications.  
                    moindex_obj.setText(str(self.moindex_content))                                        
                    moindex_obj.reindexObject() 
                    if self.exception_list:  
                        LOG('Following Exceptions occurs : ', INFO, str(self.exception_list))          
                        return 'Following Exceptions occurs : ' + str(self.exception_list)
                    else: return 'Course created SucessFully at : ' + str(course_obj.virtual_url_path())  
                else: 
                    LOG('File not Found : ', INFO, self.cloned_dir_path)
                    
        except Exception, e:
            self.exception_list.append(str(course_obj.title) + ": " + str(e))
            LOG('Following Exceptions occurs : ', INFO, str(self.exception_list))
            return 'Following Exceptions occurs : ' + str(self.exception_list)
        
class navigation:
    ''' Class to create navigation Buttons'''
    
    def __init__(self, obj, pulling, tag_list, exception_list, id_obj_dict=None, next_count_list=None, previous_count_list=None ):
        self.back_button = ''
        self.continue_button = ''
        self.top_back_button = ''
        self.top_continue_button = ''
        self.bottom_nav_buttons = ''
        self.pulling = pulling
        self.tag_list = tag_list
        self.id_obj_dict = id_obj_dict        
        self.next_count_list = next_count_list
        self.previous_count_list = previous_count_list
        self.exception_list = exception_list
        self.createBackContinueButtons(obj)
        
    def createBackContinueButtons(self, obj):
        '''function to create the Back and Continue buttons using previous and next url ''' 
  
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
            self.exception_list.append(str(obj.title) + ": " + str(e))
            LOG('createBackContinueButtons : ', INFO, str(obj.short_page_title) + ": " + str(e))            
        return
 
    def createNextUrlforFlp(self, obj):
        '''function to create the url of next FLP ''' 
        
        path = obj.virtual_url_path()
        count = 0
        next_id = ''
        for tag_dict in self.tag_list:
          try:
            key, tag = tag_dict.items()[0]          
            if (obj.id == key) and (count not in self.next_count_list):  # check to match the key with the current FLP Id                 
                self.next_count_list.append(count)
                if count == (len(self.tag_list) - 1):     # check to set the next url of Last FLP                
                    return '', ''
                
                elif tag[0] == 'sequential':   # Check to find the next FLP of the TLP.(specifically done for USERFLOW change))
                    if (count + 2) <= (len(self.tag_list) - 1):
                        next_id, next_tag = self.tag_list[count + 2].items()[0]
                    else: return '',''
                    
                    if next_tag[0] in ('html', 'problem'): return '/' + path + '/' + createId(next_id), next_tag[1]
                    elif next_tag[0] == 'sequential':
                        url = path.split('/')[:-1]   
                        return '/' + '/'.join(url) + '/' + createId(next_id), next_tag[1]
                    elif next_tag[0] == 'chapter' :
                        url = path.split('/')[:-2]   
                        return '/' + '/'.join(url) + '/' + createId(next_id), next_tag[1]
                else:
                    next_id, next_tag = self.tag_list[count + 1].items()[0]
                if tag[0] == 'chapter':
                    return '/' + path + '/' + createId(next_id), next_tag[1]
                
                elif next_tag[0] in ('html', 'problem'):                      # condition to set the next url on the basis of its tag   
                    url = path.split('/')[:-1]   
                    return '/' + '/'.join(url) + '/' + createId(next_id), next_tag[1]
                   
                elif next_tag[0] == 'sequential' :
                    url = path.split('/')[:-2]   
                    return '/' + '/'.join(url) + '/' + createId(next_id), next_tag[1]                
                   
                else :  
                     url = path.split('/')[:-3]   
                     return '/' + '/'.join(url) + '/' + createId(next_id), next_tag[1]
            count += 1
          except Exception, e:
              self.exception_list.append(str(course_obj.title) + ": " + str(e))
              LOG('createNextUrlforFlp : ', INFO, str(obj.short_page_title) + ": " + str(e))
                         
    def createPreviousUrl(self, obj):
        '''function to create the url of Previous FLP ''' 
        
        count = 0
        previous_id = ''
        for tag_dict in self.tag_list:
          try:
            key, tag = tag_dict.items()[0] 
                   
            if (obj.id == key) and (count not in self.previous_count_list):     # checking if the key is similar to current section ID               
                self.previous_count_list.append(count)            
                if count == 0: return '', ''     # check to set the previous url of First Section   
                                 
                elif self.tag_list[count - 2].values()[0][0] == 'sequential' :    # Check to find the previous of the first FLP created.(specifically done for USERFLOW change))                               
                    previous_id, previous_tup = self.tag_list[count - 2].items()[0]
                    
                else:previous_id, previous_tup = self.tag_list[count - 1].items()[0]
                if previous_id in self.id_obj_dict.keys():
                    previous_obj = self.id_obj_dict[previous_id]                  
                    return '/' + previous_obj.virtual_url_path(), previous_tup[1]
            count += 1
          except Exception, e:
              self.exception_list.append(str(course_obj.title) + ": " + str(e))
              LOG('createPreviousUrl : ', INFO, str(obj.short_page_title) + ": " + str(e)) 
