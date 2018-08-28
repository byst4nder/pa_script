#coding=utf-8
import os
import PA_runtime
import datetime
import time
from PA_runtime import *
import logging
import sqlite3
from System.Linq import Enumerable
from model_mails import MM,Mails,Accounts,Contact,MailFolder,Attach,Generate

SQL_ASSOCIATE_TABLE_MAILS = '''
    select distinct i.*,j.downloadUtc,j.downloadSize,j.mailUtc,j.name as attach_name,j.exchangeField,j.object from (
        select distinct g.*,h.attachId from (
            select distinct e.*,f.content from (
                select distinct c.* , d.showName as mailFolder from (
                    select distinct a.mailId,a.accountId,a.subject,a.abstract,a.folderId,a.fromEmail,a.receivedUtc,a.size,a.tos,a.ccs,a.bcc,a.ip,a.isForward,a.isRead,a.isRecalled,a.sendStatus,b.name as accountEmail,b.alias from
                    FM_MailInfo as a left join FM_Account as b on a.accountId = b.id)
                as c left join FM_folder as d on c.folderId = d.id)
            as e left join FM_Mail_Content as f on e.mailId = f.mailId)
        as g left join FM_Mail_PartInfo as h on g.mailId = h.mailId)
    as i left join FM_Mail_Attach as j on i.attachId = j.attachId '''

SQL_ASSOCIATE_TABLE_ACCOUNTS = '''
    select distinct a.id, a.alias, a.name as accountEmail, a.syncUtc as loginDate, b.accountImage, b.accountSign from
        FM_Account as a left join FM_Account_Setting as b on a.id = b.id'''

SQL_ASSOCIATE_TABLE_CONTACT1 = """attach database '"""

SQL_ASSOCIATE_TABLE_CONTACT2 = """' as 'FMailDB';"""

SQL_ASSOCIATE_TABLE_CONTACT3 = """
    select e.*, f.alias, f.name as accountEmail from (
        select c.*,d.name as groupName from (
            select a.accountid, a.name as contactName, a.birthday as contactBirthday,
            a.department as contactDepartment, a.familyAddress as contactFamilyAddress,
            a.mark as contactMark, a.mobile as contactMobile, a.telephone as contactTelephone,
            b.contactgroup as contactGroup, b.email as contactEmail, b.nick as contactNick from
            FMContact as a left join FMContactItem as b on a.contactid = b.contactid)
            as c left join FMContactGroup as d on c.contactgroup = d.groupid)
        as e inner join FMailDB.FM_Account
    as f on e.accountid = f.id"""

SQL_ASSOCIATE_TABLE_MAIL_FOLDER = '''select distinct a.id, a.folderType, a.showName as folderName, b.alias as accountNick, b.name as accountEmail from 
    FM_Folder as a left join FM_Account as b'''

SQL_ASSOCIATE_TABLE_ATTACH = '''select c.*, d.showName as emailFolder from (
    select b.alias as accountNick, b.name as accountEmail, a.* from (
        select distinct accountId, subject, downloadUtc, downloadSize, folderId, fromEmail, fromNick, mailUtc, 
        name as attachName, exchangeField, type as attachType from FM_Mail_Attach) 
        as a left join FM_Account as b on a.accountId = b.id) 
    as c left join FM_Folder as d on c.folderId = d.id'''


class MailParser(object):
    def __init__(self, node, extractDeleted, extractSource):
        self.node = node
        self.attachNode = None
        self.extractDeleted = extractDeleted
        self.extractSource = extractSource
        self.db = None
        self.mm = MM()
        self.cachepath = ds.OpenCachePath("QQMAIL")
        self.cachedb = self.cachepath + "\\QQMail.db"
        self.mm.db_create(self.cachedb) 
        self.mm.db_create_table()

    def analyze_mails(self):		  
        mailsNode = self.node.GetByPath("/Documents/FMailDB.db")
        if(mailsNode is None):
            return 
        mailsPath = mailsNode.PathWithMountPoint
        self.db = sqlite3.connect(mailsPath)
        mails = Mails()
        try:
            if self.db is None:
                return []
            cursor = self.db.cursor()
            cursor.execute(SQL_ASSOCIATE_TABLE_MAILS)
            for row in cursor:
                mails.mailId = row[0]
                mails.accountId = row[1]
                mails.subject = row[2]  #邮件标题
                mails.abstract = row[3]  #邮件摘要
                mails.fromEmail = row[5]  #发件人邮箱
                mails.receiveUtc = row[6]  #收件时间
                mails.size = row[7]  #邮件大小
                mails.tos = row[8]  #收件人信息（"收件人昵称"<收件人邮箱>）
                mails.cc = row[9]
                mails.bcc = row[10]
                mails.ip = row[11]  #收件人ip
                mails.isForward = row[12]
                mails.isRead = row[13]
                mails.isRecalled = row[14]
                mails.sendStatus = row[15]
                mails.account_email = row[16]  #账户邮箱
                mails.alias = row[17]  #账户昵称
                mails.mail_folder = row[18]  #邮件所属文件夹（收件箱、发件箱、星标邮箱、自定义邮箱等）
                mails.content = row[19]  #邮件正文（html格式）
                mails.downloadUtc = row[21]  #附件下载时间
                mails.downloadSize = row[22]  #附件下载大小
                mails.attachName = row[24]  #附件名
                mails.exchangeField = row[25]  #附件路径
                self.attachNode = self.node.GetByPath("/Documents/attachmentCacheFolder/").PathWithMountPoint
                mails.attachDir = self.attachNode + '''\\Documents\\attachmentCacheFolder\\ '''+ str(row[1]) if row[24] is not None else None
                self.mm.db_insert_table_mails(mails)
            self.mm.db_commit()
        except Exception as e:
            logging.error(e)
        return mails

    def analyze_mail_accounts(self):
        """
        邮箱账户
        """   
        mailsNode = self.node.GetByPath("/Documents/FMailDB.db")   #获取结点路径
        if mailsNode is None:
            return
        mailsPath = mailsNode.PathWithMountPoint
        self.db = sqlite3.connect(mailsPath)
        accounts = Accounts()
        try:
            if self.db is None:
               return []
            cursor = self.db.cursor()
            cursor.execute(SQL_ASSOCIATE_TABLE_ACCOUNTS)
            for row in cursor:
                accounts.accountId = row[0]
                accounts.alias = row[1]  #账户昵称
                accounts.accountEmail = row[2]  #账户邮箱
                accounts.loginDate = row[3]  #登陆时间
                accounts.accountImage = row[4]  #账户头像
                accounts.accountSign = row[5]  #账户登陆信息（密码之类的）
                self.mm.db_insert_table_account(accounts)
            self.mm.db_commit()
        except Exception as e:
            logging.error(e)
        return accounts

    def analyze_mail_contract(self):
        """
        邮箱联系人
        """
        contactNode = self.node.GetByPath("/Documents/FMContact.db")
        mailsNode = self.node.GetByPath("/Documents/FMailDB.db")
        if contactNode is None:
            return
        contactPath = contactNode.PathWithMountPoint
        mailsPath = mailsNode.PathWithMountPoint
        self.db = sqlite3.connect(contactPath)
        contact = Contact()
        try:
            cursor = self.db.cursor()
            SQL_ASSOCIATE_TABLE_CONTACT = SQL_ASSOCIATE_TABLE_CONTACT1 + mailsPath + SQL_ASSOCIATE_TABLE_CONTACT2
            cursor.execute(SQL_ASSOCIATE_TABLE_CONTACT)
            cursor.execute(SQL_ASSOCIATE_TABLE_CONTACT3)
            for row in cursor:
                contact.contactName = row[1]
                contact.contactBirthday = row[2]
                contact.contactDepartment = row[3]
                contact.contactFamilyAddress = row[4]
                contact.contactMark = row[5]
                contact.contactMobile = row[6]
                contact.contactTelephone = row[7]
                contact.contactEmail = row[9]
                contact.contactNick = row[10]
                contact.groupName = row[11]
                contact.alias = row[12]
                contact.accountEmail = row[13]
                self.mm.db_insert_table_contact(contact)
            self.mm.db_commit()
        except Exception as e:
            logging.error(e)
        return contact

    def analyze_mail_Folder(self):
        """
        邮件分类
        """
        mailsNode = self.node.GetByPath("/Documents/FMailDB.db")
        if mailsNode is None:
            return 
        mailsPath = mailsNode.PathWithMountPoint
        self.db = sqlite3.connect(mailsPath)
        mailFolder = MailFolder()
        try:
            cursor = self.db.cursor()
            cursor.execute(SQL_ASSOCIATE_TABLE_MAIL_FOLDER)
            for row in cursor:
                mailFolder.folderTytpe = row[1]  #邮箱类型
                mailFolder.folderName = row[2]  #邮箱分类名
                mailFolder.accountNick = row[3]  #邮箱分类所属账户昵称
                mailFolder.accountEmail = row[4]  #邮箱分类所属账户邮箱
                self.mm.db_insert_table_mail_folder(mailFolder)
            self.mm.db_commit()
        except Exception as e:
            logging.error(e)
        return mailFolder

    def analyze_mail_attach(self):
        """
        邮件附件
        """
        mailsNode = self.node.GetByPath("/Documents/FMailDB.db")
        if mailsNode is None:
            return
        mailsPath = mailsNode.PathWithMountPoint
        self.db = sqlite3.connect(mailsPath)
        attach = Attach()
        try:
            cursor = self.db.cursor()
            cursor.execute(SQL_ASSOCIATE_TABLE_ATTACH)
            for row in cursor:
                attach.accountNick = row[0]  #账户昵称
                attach.acocuntEmail = row[1] #账户邮箱
                attach.subject = row[3]  #邮件标题
                attach.downloadUtc = row[4]  #附件下载时间
                attach.downloadSize = row[5]  #附件大小
                attach.fromEmail = row[7]  #发件人邮箱
                attach.fromNick = row[8]  #发件人昵称
                attach.mailUtc = row[9]  #收件时间
                attach.attachName = row[10]  #附件名称
                attach.exchangeField = row[11]  #附件路径
                attach.attachType = row[12]  #附件类型
                attach.emailFolder = row[13]  #邮件类型
                self.mm.db_insert_table_attach(attach)
            self.mm.db_commit()
        except Exception as e:
            logging.error(e)
        return attach

    def analyze_mail_search(self):
        """
        邮件搜索
        """
        pass


    def parse(self):
        self.analyze_mails()
        self.analyze_mail_accounts()
        self.analyze_mail_contract()
        self.analyze_mail_Folder()
        self.analyze_mail_attach()
        self.analyze_mail_search()
        self.mm.db_close()
        self.db.commit()
        self.db.close()

        generate = Generate(self.cachedb)
        models = generate.get_models()
        return []
    




def analyze_qqmail(node, extractDeleted, extractSource):
    pr = ParserResults()
    pr.Models.AddRange(MailParser(node, extractDeleted, extractSource).parse())
    return pr