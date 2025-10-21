#!/usr/bin/env python

# Stemwijzer scraper

# Import dependencies
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementNotInteractableException
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

from datetime import datetime, date
from io import StringIO

from abc import ABC, abstractmethod

import pandas as pd

import re
import json
import subprocess
import time
import math

# Scraper classes
class BaseSelector(ABC):
    @abstractmethod
    def scrape(self, scraper, parent, **kwargs):
        pass

class AttributeSelector(BaseSelector):
    def __init__(self, id, by, path, attribute, multiple=False, default=None):
        self.id = id
        self.by = by
        self.path = path
        self.attribute = attribute
        self.multiple = multiple
        self.default = default

    def scrape(self, scraper, parent, **kwargs):
        try:
            WebDriverWait(parent, 100).until(lambda driver: driver.find_element(self.by, self.path.format(**kwargs)))
        except TimeoutException:
            return [] if self.multiple else self.default
        if not self.multiple:
            try:
                elem = parent.find_element(self.by, self.path.format(**kwargs))
                return {self.id: elem.get_attribute(self.attribute)}
            except NoSuchElementException:
                return self.default
        else:
            elems = parent.find_elements(self.by, self.path.format(**kwargs))
            return [{self.id: elem.get_attribute(self.attribute)} for elem in elems]

class TextSelector(AttributeSelector):
    def __init__(self, id, by, path, multiple=False, default=None):
        super().__init__(id, by, path, 'innerText', multiple, default)

class MapSelector(BaseSelector):
    def __init__(self, fun, child):
        self.fun = fun
        self.child = child

    def scrape(self, scraper, parent, **kwargs):
        data = self.child.scrape(scraper, parent, **kwargs)
        if type(data) == dict:
            return self.fun(data)
        return list(map(self.fun, data))

class FilterSelector(BaseSelector):
    def __init__(self, fun, child):
        self.fun = fun
        self.child = child

    def scrape(self, scraper, parent, **kwargs):
        data = self.child.scrape(scraper, parent, **kwargs)
        return list(filter(self.fun, data))

class ZipSelector(BaseSelector):
    def __init__(self, left, right):
        self.left = left
        self.right = right
        
    def scrape(self, scraper, parent, **kwargs):
        data_left = self.left.scrape(scraper, parent, **kwargs)
        data_right = self.right.scrape(scraper, parent, **kwargs)
        
        if type(data_left) == dict and type(data_right) == dict:
            return data_left | data_right
        elif type(data_left) == dict and type(data_right) == list:
            return [data_left | m for m in data_right]
        elif type(data_left) == list and type(data_right) == dict:
            return [m | data_right for m in data_left]
        return [data_left[i] | data_right[i] for i in range(min(len(data_left),len(data_right)))]

class URLSelector(BaseSelector):
    def __init__(self, urls, child):
        self.urls = urls
        self.child = child
        
    def scrape(self, scraper, parent, **kwargs):
        result = []
        
        for url in self.urls:
            scraper.get(url.format(**kwargs))
            data = self.child.scrape(scraper, scraper, **kwargs)
            
            if type(data) == dict:
                result.append(data)
            elif type(data) == list:
                result.extend(data)
            
        return result[0] if len(self.urls) == 1 and type(data) == dict else result

class ConstantSelector(BaseSelector):
    def __init__(self, value={}):
        self.value = value
        
    def scrape(self, scraper, parent, **kwargs):
        if type(self.value) == str:
            return self.value.format(**kwargs)
        elif type(self.value) == dict:
            return {k.format(**kwargs): v.format(**kwargs) for k, v in self.value.items()}
        else:
            return self.value

class SelectByVisibleTextSelector(BaseSelector):
    def __init__(self, by, path, text, child, multiple=False):
        self.by = by
        self.path = path
        self.text = text
        self.child = child
        self.multiple = multiple
        
    def scrape(self, scraper, parent, **kwargs):
        WebDriverWait(parent, 100).until(lambda driver: driver.find_element(self.by, self.path.format(**kwargs)))
        if not self.multiple:            
            elem = parent.find_element(self.by, self.path.format(**kwargs))
            Select(elem).select_by_visible_text(self.text.format(**kwargs))
            return self.child.scrape(scraper, parent, **kwargs)
        else:
            elems = parent.find_elements(self.by, self.path.format(**kwargs))
            for elem in elems:
                Select(elem).select_by_visible_text(self.text.format(**kwargs))
            return self.child.scrape(scraper, parent, **kwargs)

class SetCheckboxSelector(BaseSelector):
    def __init__(self, by, path, value, child, multiple=False):
        self.by = by
        self.path = path
        self.value = value
        self.child = child
        self.multiple = multiple

    def click(self, driver, elem):
        try:
            elem.click() # Try the selenium method first
        except (ElementNotInteractableException, ElementClickInterceptedException) as e:
            driver.execute_script("arguments[0].click();", elem)
    
    def scrape(self, scraper, parent, **kwargs):
        WebDriverWait(parent, 100).until(lambda driver: driver.find_element(self.by, self.path.format(**kwargs)))
        if not self.multiple:            
            elem = parent.find_element(self.by, self.path.format(**kwargs))
            if elem.is_selected() != self.value:
                self.click(parent, elem)
        else:
            elems = parent.find_elements(self.by, self.path.format(**kwargs))
            for elem in elems:
                if elem.is_selected() != self.value:
                    self.click(parent, elem)
        return self.child.scrape(scraper, parent, **kwargs)

class ClickSelector(BaseSelector):
    def __init__(self, by, path, child, multiple=False):
        self.by = by
        self.path = path
        self.child = child
        self.multiple = multiple

    def click(self, driver, elem):
        try:
            elem.click() # Try the selenium method first
        except (ElementNotInteractableException, ElementClickInterceptedException) as e:
            driver.execute_script("arguments[0].click();", elem)
    
    def scrape(self, scraper, parent, **kwargs):
        WebDriverWait(parent, 100).until(lambda driver: driver.find_element(self.by, self.path.format(**kwargs)))
        if not self.multiple:            
            elem = parent.find_element(self.by, self.path.format(**kwargs))
            self.click(parent, elem)
        else:
            elems = parent.find_elements(self.by, self.path.format(**kwargs))
            for elem in elems:
                self.click(parent, elem)
        return self.child.scrape(scraper, parent, **kwargs)

class TableSelector(BaseSelector):
    def __init__(self, by, path):
        self.by = by
        self.path = path
    
    def scrape(self, scraper, parent, **kwargs):
        try:
            WebDriverWait(parent, 100).until(lambda driver: driver.find_element(self.by, self.path.format(**kwargs)))
            elem = parent.find_element(self.by, self.path.format(**kwargs))
            df = pd.read_html(StringIO(elem.get_attribute("outerHTML")))[0]
            return df.to_dict(orient='records')
        except TimeoutException:
            return []

class SleepSelector(BaseSelector):
    def __init__(self, seconds, child):
        self.seconds = seconds
        self.child = child

    def scrape(self, scraper, parent, **kwargs):
        time.sleep(self.seconds)
        return self.child.scrape(scraper, parent, **kwargs)

class KeySelector(BaseSelector):
    def __init__(self, key, child):
        self.key = key
        self.child = child

    def scrape(self, scraper, parent, **kwargs):
        value = self.child.scrape(scraper, parent, **kwargs)
        return { self.key: value }

class IfExistsSelector(BaseSelector):
    def __init__(self, by, path, child_if, child_not):
        self.by = by
        self.path = path
        self.child_if = child_if
        self.child_not = child_not

    def scrape(self, scraper, parent, **kwargs):
        if parent.find_elements(self.by, self.path.format(**kwargs)):
            return self.child_if.scrape(scraper, parent, **kwargs)
        return self.child_not.scrape(scraper, parent, **kwargs)

class LoopSelector(BaseSelector):
    def __init__(self, by, path, child):
        self.by = by
        self.path = path
        self.child = child
        self.click_selector = ClickSelector(by, path, ConstantSelector([]))

    def scrape(self, scraper, parent, **kwargs):
        result = []
        while True:
            child_res = self.child.scrape(scraper, parent, **kwargs)
            if type(child_res) == list:
                result += child_res
            else:
                result.append(child_res)
            if not parent.find_elements(self.by, self.path.format(**kwargs)):
                break
            self.click_selector.scrape(scraper, parent, **kwargs)
        return result

class RangeSelector(BaseSelector):
    def __init__(self, name, start, end, step, child):
        self.name = name
        self.start = start
        self.end = end
        self.step = step
        self.child = child
        
    def scrape(self, scraper, parent, **kwargs):
        result = []
        for i in range(self.start, self.end, self.step):
            child_res = self.child.scrape(scraper, parent, **(kwargs | { self.name: i }))
            if type(child_res) == list:
                result += child_res
            else:
                result.append(child_res)
        return result

class EnrichSelector(BaseSelector):
    def __init__(self, child_source, child_enrich):
        self.child_source = child_source
        self.child_enrich = child_enrich

    def scrape(self, scraper, parent, **kwargs):
        data = self.child_source.scrape(scraper, parent, **kwargs)
        enricher = lambda e: self.child_enrich.scrape(scraper, parent, **(kwargs | e)) | e
        return list(map(enricher, data))

# Scraper definition
scraper = ClickSelector(By.CLASS_NAME, "start__button", 
    SleepSelector(3, 
        LoopSelector(By.CLASS_NAME, "statement__skip", 
            SleepSelector(3,
                IfExistsSelector(By.CLASS_NAME, "statement__skip",
                    ZipSelector(
                        TextSelector("theme", By.CLASS_NAME, "statement__theme"), 
                        ZipSelector(
                            MapSelector(lambda d: {'title': re.sub(r'\s+', ' ', d['title'].strip())}, AttributeSelector("title", By.CLASS_NAME, "statement__title", "aria-label")),
                            ClickSelector(By.CLASS_NAME, "statement__tab-button--more-info", 
                                ZipSelector(
                                    TextSelector("info", By.CLASS_NAME, "statement__tab-text"),
                                    ClickSelector(By.CLASS_NAME, "statement__tab-button--parties", 
                                        ClickSelector(By.XPATH, '//*[@id="app"]/div/div/div[2]/div/div[position() >= 2]/button', 
                                            KeySelector('positions',
                                                RangeSelector("i", 1, 4, 1, 
                                                    IfExistsSelector(By.XPATH, '//*[@id="app"]/div/div/div[2]/div[{i}]/div[position() >= 2]/div', 
                                                        ZipSelector(
                                                            TextSelector("position", By.XPATH, '//*[@id="app"]/div/div/div[2]/div[{i}]/div[1]/h2'),
                                                            ZipSelector(
                                                                TextSelector("party", By.XPATH, '//*[@id="app"]/div/div/div[2]/div[{i}]/div[position() >= 2]/button/h2', multiple=True),
                                                                TextSelector("explanation", By.XPATH, '//*[@id="app"]/div/div/div[2]/div[{i}]/div[position() >= 2]/div', multiple=True)
                                                            )
                                                        ), 
                                                        ConstantSelector([])
                                                    )
                                                )
                                            ), multiple=True
                                        )
                                    )
                                )
                            )
                        )
                    ),
                    ConstantSelector([])
                )
            )
        )
    )
)

if __name__ == "__main__":
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get("https://tweedekamer2025.stemwijzer.nl")
    
    # Execute scraper
    data = scraper.scrape(driver, driver)
    
    # Save as JSON
    with open('tweedekamer2025.json', 'w') as f:
        json.dump(data, f, indent=4, default=str)

    driver.close()