#!/usr/bin/env python
# Filename: site_backup.py
# Author: Aaron Levie, aaron@leviedesigns.com
# Date: 2014-05-21
# Description: This script reads parameters from a config file and uses them to backup websites (mysql and files)
# Dependancies: server must have python, mysqldump, tar, and gzip
#   files:      site_backup.cfg
#   libraries:  ConfigParser, time, os, subprocess
# Execution: run with python (preferebly using cron)
# Arguments: None
# Supported OS: Should work on any linux distro. Tested on CentOS/Debian.

from argparse import ArgumentParser
import ConfigParser
import time
import os
import subprocess

class BackupSites:
  def __init__(self):
    self.time = time.strftime('%Y%m%d_%H%M%S',time.gmtime()) #timestamp used in filenames
    self.cfile = 'site_backup.cfg'
    self.shutup = open(os.devnull, 'w')
    self.parse_config()
    self.loop_sites()
    self.close()

  def parse_config(self):
    #parses config file
    if os.path.isfile(self.cfile):
      self.config = ConfigParser.RawConfigParser()
      self.config.read(self.cfile)
      self.delete_after = self.config.get('main', 'keepdays')
    else:
      raise Exception('Config file \'%s\' could not be found' % self.cfile)

  def loop_sites(self):
    #iterate over all sites specified in config file
    for section in self.config.sections():
      if section != 'main':
        dir_backup = self.config.get(section, 'dir_backup')
        self.mkdir(dir_backup)
        sql_file = self.dump_db(section)
        self.make_tar(section,sql_file)
        self.cleanup(dir_backup)

  def mkdir(self,dirname):
    #creates site directory for storing backups 
    if not os.path.isdir(dirname):
      os.mkdir(dirname)

  def dump_db(self,section):
    #gets dump of the db
    if not self.config.has_option(section, 'dir_backup'):
      raise Exception('\'dir_backup\' option not found in \'%s\' section' % section)
    if self.config.has_option(section, 'dbhost'):
      if not self.config.has_option(section, 'dbuser'):
        raise Exception('\'dbuser\' option not found in \'%s\' section' % section)
      if not self.config.has_option(section, 'dbpass'):
        raise Exception('\'dbpass\' option not found in \'%s\' section' % section)
      if not self.config.has_option(section, 'dbname'):
        raise Exception('\'dbname\' option not found in \'%s\' section' % section)
    else:
      return False
    dir_backup = self.config.get(section, 'dir_backup')
    db_host = self.config.get(section, 'dbhost')
    db_user = self.config.get(section, 'dbuser')
    db_pass = self.config.get(section, 'dbpass')
    db_name = self.config.get(section, 'dbname')
    sql_file = os.path.join(dir_backup, '%s_%sUTC.sql' % (section,self.time))
    out_file = open(sql_file, 'wb')
    self.execute(['mysqldump', '-h', db_host, '-u', db_user, '--password='+db_pass, db_name], out_file)
    out_file.close()
    return sql_file
    
  def make_tar(self,section,sql_file=False):
    #creates tar file
    site_dir_path = os.path.abspath(self.config.get(section, 'dir_htdocs'))
    dir_backup = self.config.get(section, 'dir_backup')
    cd1_path = os.path.dirname(site_dir_path)
    site_dir_parent = os.path.basename(os.path.normpath(site_dir_path))
    tar_path = os.path.join(os.path.abspath(dir_backup), '%s_%sUTC.tar' % (section,self.time))
    if sql_file != False:
      sql_file_path = os.path.abspath(sql_file)
      sql_file_name= os.path.basename(os.path.normpath(sql_file_path))
    cd2_path = dir_backup
    command = ['tar', '-cvf', tar_path]
    for i in range(1,10):
      try:
        temp = self.config.get(section, 'exclude%s' % i)
      except:
        pass
      else:
        command += ['--exclude', temp]
    command += ['-C', cd1_path, site_dir_parent]
    self.execute(command, self.shutup) #create tar of site files
    if sql_file != False:
      self.execute(['tar', '-rvf', tar_path, '-C', cd2_path, sql_file_name], self.shutup) #append tar file with sql file
      os.remove(sql_file_path) #remove sql file
    self.execute(['gzip', tar_path], self.shutup) #zip tar file

  def execute(self,command,xstdout):
    #executes a command in terminal and outputs to xstdout argument
    temp = subprocess.Popen(command, stdout=xstdout)
    temp.communicate()

  def cleanup(self, dir_backup):
    #delete files older than X days
    self.execute(['find', dir_backup, '-mtime', '+'+self.delete_after, '-exec', 'rm', '-r', '-f', '{}', ';'], self.shutup)

  def close(self):
    #close /dev/null
    self.shutup.close()


def main():
  abspath = os.path.abspath(__file__) #gets path of this python file
  dirpath = os.path.dirname(abspath) #strips the filename
  os.chdir(dirpath) #changes the current working directory to the same as this python file
  BackupSites()


if __name__ == "__main__":
  main()