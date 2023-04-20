# -*- coding: utf-8 -*-
"""
/***************************************************************************
 PGrantManDockWidget
                                 A QGIS plugin
 Manage privileges in PostgreSQL Databases from QGIS
                             -------------------
        begin                : 2017-07-28
        git sha              : $Format:%H$
        copyright            : (C) 2017 by GISWG
        email                : info@giswg.de
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from PyQt4.QtCore import pyqtSignal

import os, sys, datetime
import traceback
import xlwt, csv, codecs
import psycopg2
#import dbConnection

from PyQt4 import QtGui, uic
from PyQt4 import QtCore
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.utils import *
from qgis.core import *
from qgis.gui import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'pgrant_man_dockwidget_base.ui'), resource_suffix='')

class PGrantManDockWidget(QtGui.QDockWidget, FORM_CLASS):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(PGrantManDockWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        self.settings = QSettings()

        self.cb_pgconns.activated.connect(self.conSelected)
        self.tw_tables.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
        self.tw_tables.itemChanged.connect(self.priv_clicked)

        self.tw_loginroles.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
        self.tree_grp_roles.setHeaderHidden(True)
        #self.tree_grp_roles.header().setStretchLastSection(False)
        #self.tree_grp_roles.header().setResizeMode(QHeaderView.ResizeToContents)
        

        self.populateDBConnections()
        self.populateLoginRoles()
        self.populateGroupRoles()

        self.priv_col_dict = {'ALL':2,
                         'INSERT':3,
                         'SELECT':4,
                         'UPDATE':5,
                         'DELETE':6,
                         'TRUNCATE':7,
                         'REFERENCES':8,
                         'TRIGGER':9}

    def conSelected(self):
        self.table_dict = {}
        self.tw_tables.setRowCount(0)
        s = self.sender()
        dbcon = s.currentText()
        self.pgConn = psycopg2.connect("dbname='{db}' host='{host}' port='{port}' user='{usr}' password='{pwd}'".format(** self.getDBParametersFromName(dbcon)))
        if self.cb_dontlistsystables.isChecked():
            all_rel = self.execSQL("""SELECT table_schema||'.'||table_name, table_type
                                            FROM information_schema.tables
                                            WHERE NOT table_schema IN ('information_schema','pg_catalog')
                                            ORDER BY table_schema, table_name""")
        else:
            all_rel = self.execSQL("""SELECT table_schema||'.'||table_name, table_type
                                            FROM information_schema.tables
                                            ORDER BY table_schema, table_name""")
        for schema_name, type in all_rel:
            self.addTableLine()
            self.tw_tables.setItem(self.nrow, 0, QTableWidgetItem(schema_name))
            self.tw_tables.setItem(self.nrow, 1, QTableWidgetItem(type))
            for c in range(2, 10):
                self.tw_tables.setCellWidget(self.nrow, c, QCheckBox())
            tabkey = schema_name
            self.table_dict[tabkey] = {}
            self.table_dict[tabkey]['row'] = self.nrow
            for p in ['ALL','INSERT','SELECT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER']:
                self.table_dict[tabkey][p] = False

        res = self.execSQL("""SELECT table_schema||'.'||table_name, privilege_type FROM information_schema.role_table_grants WHERE grantee = 'postgres'""")
        for schema_name, priv in res:
            print schema_name, priv
            self.tw_tables.cellWidget(self.table_dict[schema_name]['row'], self.priv_col_dict[priv]).setChecked(2)

    def populateDBConnections(self):
        # populate the combo with connections
        self.cb_pgconns.clear()
        s = QSettings()
        s.beginGroup("PostgreSQL/connections")
        dbnames = s.childGroups()
        s.endGroup()
        for d in dbnames:
            con = self.getDBParametersFromName(d)
            #list only connection with appropriate privileges
            if con['usr'] == 'postgres':
                try:
                    self.pgConn = psycopg2.connect("dbname='{db}' host='{host}' port='{port}' user='{usr}' password='{pwd}'".format(** self.getDBParametersFromName(d)))
                    self.cb_pgconns.addItem(d)
                except:
                    print('Keine Verbindung zu "{0}"'.format(d))

    def populateLoginRoles(self):
        params = {}
        l_roles = self.execSQL("""SELECT rolname, description FROM pg_roles r
                                    LEFT OUTER JOIN pg_shdescription c ON c.objoid = r.oid
                                    WHERE r.rolcanlogin ORDER BY rolname;""")
        r = 0
        for u, d in l_roles:
            params['user'] = u
            res = self.execSQL("""SELECT pg_get_userbyid(a.oid) AS role
                                    FROM pg_authid a
                                    WHERE pg_has_role('{user}', a.oid, 'member') AND pg_get_userbyid(a.oid) != '{user}'
                                    ORDER BY role;""".format(** params))

            membership = ', '.join([i[0] for i in res])
            self.tw_loginroles.setRowCount(self.tw_loginroles.rowCount() + 1)
            self.tw_loginroles.setItem(r, 0, QTableWidgetItem(u))
            self.tw_loginroles.setItem(r, 1, QTableWidgetItem((d or '').replace('\n', ' | ')))
            self.tw_loginroles.setItem(r, 2, QTableWidgetItem(membership))
            r += 1

    def populateGroupRoles(self):
        params = {}
        g_roles = self.execSQL("""SELECT rolname, description FROM pg_roles r
                                            LEFT OUTER JOIN pg_shdescription c ON c.objoid = r.oid
                                            WHERE NOT r.rolcanlogin ORDER BY rolname;""")
        top_lvl_itm = QTreeWidgetItem('group roles')
        self.tree_grp_roles.addTopLevelItem(top_lvl_itm)
        
        for r, d in g_roles:
            print '%s: %s' % (r, (d or '').replace('\n', ' | '))
            i = QTreeWidgetItem('%s: %s' % (r, (d or '').replace('\n', ' | ')))
            top_lvl_itm.addChild(i)
            
        #for i in range(0, self.tree_grp_roles.columnCount()):
        #    self.tree_grp_roles.resizeColumnToContents(i)

    def findGrpRoleMembers(self, rolname, treeItem):
        pass

    def priv_clicked(self):
        s = self.sender()
        print s

    def getDBParametersFromName(self, conname):
        database = self.settings.value('PostgreSQL//connections//%s//database' % conname)
        username = self.settings.value('PostgreSQL//connections//%s//username' % conname)
        password = self.settings.value('PostgreSQL//connections//%s//password' % conname)
        host = self.settings.value('PostgreSQL//connections//%s//host' % conname)
        port = self.settings.value('PostgreSQL//connections//%s//port' % conname)
        return {'db':database, 'host':host, 'port':port, 'usr':username, 'pwd':password}

    def addTableLine(self):
        self.tw_tables.setRowCount(self.tw_tables.rowCount() + 1)
        self.nrow = self.tw_tables.rowCount() - 1

    def execSQL(self, sql):
        cur = self.pgConn.cursor()
        cur.execute(sql)
        return cur.fetchall()

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

