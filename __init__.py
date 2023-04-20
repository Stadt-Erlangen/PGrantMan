# -*- coding: utf-8 -*-
"""
/***************************************************************************
 PGrantMan
                                 A QGIS plugin
 Manage privileges in PostgreSQL Databases from QGIS
                             -------------------
        begin                : 2017-07-28
        copyright            : (C) 2017 by GISWG
        email                : info@giswg.de
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load PGrantMan class from file PGrantMan.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .pgrant_man import PGrantMan
    return PGrantMan(iface)
