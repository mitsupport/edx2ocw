from lxml import etree
from zLOG import LOG, INFO, DEBUG
import re


def getModifiedAssessmentString(self, file_path, flag=False):
    """ Calls the OpenAssessments Converter """
    LOG('getModifiedAssessmentString : ', INFO, "started")
    convertedXMLstring = ""
    
    try:
        tree = etree.parse(file_path)
        header_text = tree.getroot().attrib['display_name']
        problemDiv = ''
        problem_header = '<h2 class="subhead">' + header_text + '</h2>'
        h2_list = tree.findall(".//h2")   
        prob_count_type_dict = {}  
        solution_div_list = []
        if h2_list and filter(lambda x: x.text == header_text, h2_list) : problem_header = '' # code to add the Headers in Problem section if the sub head is not present in the content 
        
        tree_string = etree.tostring(tree)
        tree_string = re.sub(r'<problem.*?>', r'<div class="self_assessment">', tree_string)
        tree_string = re.sub(r'</problem>', r'</div>', tree_string)
                           
        root = etree.XML(tree_string)              
        if not flag:
            self.problem_count = 0;
            self.solution_count = 0;
            self.problem_btns_count = 1;
            
        for element in root.xpath('//solution'): 
                self.solution_count += 1
                solution_txt = etree.tostring(element)            
                solution_txt = solution_txt.replace('<solution', '<div id="S' + str(self.solution_count) + '_div" class="problem_solution" tabindex="-1"')  
                solution_txt = solution_txt.replace('</solution>', '</div>')             
                
                solution_div_list.append(self.solution_count)
                solutionDiv = etree.fromstring(solution_txt)            
                element.getparent().replace(element, solutionDiv);
            
        for element in root.xpath('//script'):
            element.getparent().remove(element)
        
        context = etree.iterwalk(root)  
        for action, element in context:
             
            if element.tag == 'optionresponse':
                self.problem_count += 1                
                correct_option = ""
                options = ""
                for child in element:
                    if child.tag == 'optioninput':
                        correct_option = child.get('correct','')
                        options = child.get('options')
                
                #remove parenthesis
                options = options[1:-1]
                options =  re.sub('\' +,','\',',options)
                options = options.split('\',')
                                
                problemDiv = etree.Element('div', id='Q' + str(self.problem_count) + '_div')
                problemDiv.attrib['class'] = 'problem_question'
                select = etree.Element('select', id='Q' + str(self.problem_count) + '_select', onchange="dropDownSelected(" + str(self.problem_count) + ")")
                select.attrib['class'] = 'problem_text_input'
                
                dafault_option = etree.Element('option', value='', correct='false')
                select.append(dafault_option)
                
                ans_span = etree.Element('span', tabindex="-1", id='Q' + str(self.problem_count) + '_ans_span', style="display:none;")
                ans_span.text = "  " + correct_option
                
                status_p = etree.Element('p', tabindex="-1", id='Q' + str(self.problem_count) + '_status')
                status_p.attrib['class'] = 'nostatus'
                status_p.attrib['aria-label'] = ''
                status_p.text = ''
                
                br = etree.Element('br');
                
                for option in options:
                    option = option.strip()
                    if option[0] == "'":
                        option = option.strip()[1:]                                 #removing extra ''
                    if option[-1] == "'":
                        option = option.strip()[:-1]                                 #removing extra ''    
                        
                    option_element = etree.Element('option', value=option)
                    option_element.text = option
                    option_element.attrib['correct'] = 'false'
                    if(option == correct_option):
                        option_element.attrib['correct'] = 'true'
                    select.append(option_element)
                    
                problemDiv.append(select)
                problemDiv.append(ans_span)
                problemDiv.append(status_p)
                problemDiv.append(br)
                prob_count_type_dict[self.problem_count]= "optionresponse"
                element.getparent().replace(element, problemDiv);    
            
            if element.tag == 'stringresponse': 
                self.problem_count += 1
                
                problemDiv = etree.Element('div', id='Q' + str(self.problem_count) + '_div')
                problemDiv.attrib['class'] = 'problem_question'
                
                input_usr = etree.Element('input', type='text', answer=element.get('answer',''), ckecktype=element.get('type','') ,value='', id='Q' + str(self.problem_count) + '_input', onkeypress="numericTyped(" + str(self.problem_count) + ")")
                input_usr.attrib['class'] = 'problem_text_input'
                input_usr.attrib['aria-label'] = 'text-input'
                
                status_p = etree.Element('p', tabindex="-1", id='Q' + str(self.problem_count) + '_status')
                status_p.attrib['class'] = 'nostatus'
                status_p.attrib['aria-label'] = ''
                status_p.text = ''
                
                ans_span = etree.Element('span', id='Q' + str(self.problem_count) + '_ans_span', tabindex="-1", style="display:none;")
                ans_span.text = '  Answer:'+element.get('answer','')
                
                br = etree.Element('br');                
                
                prob_count_type_dict[self.problem_count]= "stringresponse"
                problemDiv.append(input_usr);
                problemDiv.append(status_p);
                problemDiv.append(ans_span);
                problemDiv.append(br);
                                
                element.getparent().replace(element, problemDiv);
                                    
            if element.tag == 'numericalresponse': 
                self.problem_count += 1
                pblm = {'answer':element.get('answer', ''), 'tolerance':'0'}
                for child in element:
                    if child.tag == 'responseparam':
                        pblm['tolerance'] = child.get('default','0')
                
                problemDiv = etree.Element('div', id='Q' + str(self.problem_count) + '_div')
                problemDiv.attrib['class'] = 'problem_question'
                input_usr = etree.Element('input', type='text', value='', id='Q' + str(self.problem_count) + '_input', onkeypress="numericTyped(" + str(self.problem_count) + ")")
                input_usr.attrib['class'] = 'problem_text_input'
                input_usr.attrib['aria-label'] = 'text-input'
                
                status_p = etree.Element('p', tabindex="-1", id='Q' + str(self.problem_count) + '_status')
                status_p.attrib['class'] = 'nostatus'
                status_p.attrib['aria-label'] = ''
                status_p.text = ''
                
                br = etree.Element('br');
                
                input_ans = etree.Element('input', type='hidden', value=pblm['answer'], id='Q' + str(self.problem_count) + '_ans')
                input_tolerance = etree.Element('input', type='hidden', value=pblm['tolerance'], id='Q' + str(self.problem_count) + '_tolerance')
                
                prob_count_type_dict[self.problem_count]= "numerical"                
                
                problemDiv.append(input_usr);
                problemDiv.append(status_p);
                problemDiv.append(br);
                problemDiv.append(input_ans);
                problemDiv.append(input_tolerance);
               
                #append answer to solution sdiv before explanation else to qdiv
                ans_p = etree.Element('p', id='S' + str(self.problem_count) + '_ans', tabindex="-1")
                ans_p.attrib['class'] = 'problem_answer'
                ans_p.text = ''
                problemDiv.append(ans_p);                            
                
                element.getparent().replace(element, problemDiv);                
            
            if element.tag == 'multiplechoiceresponse':                
                self.problem_count += 1
                problemDiv = etree.Element('div', id='Q' + str(self.problem_count) + '_div')
                problemDiv.attrib['class'] = 'problem_question'
                problemDiv = getNodeText(element, problemDiv)
                choice_count = 0    
                for choice in element.iter("choice"):                              
                    choice_text, node_text, child_tag = getChildNodeText(choice) 
                    choice_count += 1
                    print 'choice_count ' + str(choice_count)
                    input_id = 'Q' + str(self.problem_count) + '_input_' + str(choice_count)
                    input = etree.Element('input', type='radio', value= node_text, name='Q' + str(self.problem_count) + '_input', id=input_id, onclick='optionSelected(' + str(self.problem_count) + ')')
                    input.attrib['class'] = 'problem_radio_input'
                    input.attrib['aria-label'] = node_text
                    input.text = choice_text
                    if type(child_tag) != str:
                        input.append(child_tag);
                          
                    br = etree.Element('br');
                    status_p = etree.Element('p', id=input_id + '_status', tabindex="-1")
                    status_p.attrib['class'] = 'nostatus'
                    status_p.attrib['aria-label'] = ''
                    status_p.text = ''
                    
                    input.attrib['correct'] = 'false'                
                    if choice.get('correct') == 'true':
                        input.attrib['correct'] = 'true'
                    
                    problemDiv.append(input);
                    problemDiv.append(status_p);
                    problemDiv.append(br);                                
                
                br = etree.Element('br');
                problemDiv.append(br);#more spacing between last option and Check/Show buttons
                 
                prob_count_type_dict[self.problem_count]= "multiple_choice"
                element.getparent().replace(element, problemDiv);
                
            #code for multiple choice questions add a new attribute in input to show if it's correct or wrong
            if element.tag == 'choiceresponse':                
                self.problem_count += 1
                problemDiv = etree.Element('div', id='Q' + str(self.problem_count) + '_div')
                problemDiv.attrib['class'] = 'problem_question'
                problemDiv = getNodeText(element, problemDiv)
                choice_count = 0    
                for choice in element.iter("choice"):   
                    choice_text, node_text, child_tag = getChildNodeText(choice)
                    choice_count += 1
                    input_id = 'Q' + str(self.problem_count) + '_input_' + str(choice_count)
                    input = etree.Element('input', value=node_text, type='checkbox',name='Q' + str(self.problem_count) + '_input', id=input_id, onclick='optionSelected(' + str(self.problem_count) + ')')
                    input.attrib['class'] = 'problem_radio_input'
                    input.attrib['aria-label'] = node_text
                    input.text = choice_text
                    if type(child_tag) != str:
                        input.append(child_tag);
                           
                    br = etree.Element('br');
                    status_p = etree.Element('p', id=input_id + '_status', tabindex="-1")
                    status_p.attrib['class'] = 'nostatus'
                    status_p.attrib['aria-label'] = ''
                    status_p.text = ''
                    
                    input.attrib['correct'] = 'false'                
                    if choice.get('correct') == 'true':
                        input.attrib['correct'] = 'true'   
                    
                    problemDiv.append(input);
                    problemDiv.append(status_p);
                    problemDiv.append(br);
                
                #add a new combined status_p for entire choiceresponce
                status_p_combined = etree.Element('p', id='Q' + str(self.problem_count) + '_status_combined', tabindex="-1")
                status_p_combined.attrib['class'] = 'nostatus'
                status_p_combined.attrib['aria-label'] = ''
                status_p_combined.text = ''
                problemDiv.append(status_p_combined);
                br = etree.Element('br');
                problemDiv.append(br);                
                prob_count_type_dict[self.problem_count]= "choiceresponse"                
                element.getparent().replace(element, problemDiv);
                        
        # to append the check and show answer button in all the cases except custom response type
        if problemDiv != '':
            button_check = etree.Element('button', id='Q' + str(self.problem_btns_count) + '_button', onclick='checkAnswer(' + str(prob_count_type_dict) + ')')
            button_check.attrib['class'] = 'problem_mo_button'
            button_check.text = 'Check'
            
            button_show = etree.Element('button', id='Q' + str(self.problem_btns_count) + '_button_show', onclick='showHideSolution('  + str(prob_count_type_dict) + ', ' + str(self.problem_btns_count) + ', ' + str(solution_div_list) +')')
            button_show.attrib['class'] = 'problem_mo_button'
            button_show.text = 'Show Answer'                
    
            problemDiv.append(button_check);
            problemDiv.append(button_show);            
            self.problem_btns_count += 1
                                    
        convertedXMLstring = problem_header + etree.tostring(root)
        LOG('getModifiedAssessmentString : ', INFO, "Successfully converted problem")
        #print("Final output::"+convertedXMLstring)
        
    except Exception, e:
        LOG('getModifiedAssessmentString Exceptions : ', INFO, "Exception:" + str(e))
        raise
    return convertedXMLstring

def getChildNodeText(choice):
    '''Function to get all the child elements of choice tag'''
    
    child_tag = ''
    choice_text = ''
    node_text = ''
    for node in choice.iter():
        if node.text != None: node_text +=  node.text                   
    
    if choice.text != None:
        choice_text = choice.text
        
    if len(choice): 
        child_list = choice.getchildren()
    
        if len(child_list)>1:
            for child in child_list:                                                        
                child_list[0].append(child)
        child_tag = child_list[0]  
    
    return choice_text, node_text, child_tag

def getNodeText(element, problemDiv):
    '''Function to get the elements text '''
    
    if element.text != None: problemDiv.text =  element.text   
    if len(element): 
        child_list = element.getchildren()
        for  child in child_list:
            if child.tag not in ('checkboxgroup', 'choicegroup'):
                problemDiv.append(child);
    return problemDiv 
    
#if __name__ == '__main__':
#    getModifiedAssessmentString("assessment.xml")            
   

