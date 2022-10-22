#!/usr/bin/python3
# coding: utf-8
#
# A simple indicator applet displaying cpu and memory information
#
# Author: Alex Eftimie <alex@eftimie.ro>
# Fork Author: fossfreedom <foss.freedom@gmail.com>
# Original Homepage: http://launchpad.net/indicator-sysmonitor
# Fork Homepage: https://github.com/fossfreedom/indicator-sysmonitor
# License: GPL v3
#

import re
import logging
import os
from gettext import gettext as _
import json

from gi.repository import Gtk
from utils.config import DIR_CONFIG

from sensors import SensorManager
from sensors import ISMError

__version__ = '0.9.1'


def raise_dialog(parent, flags, type_, buttons, msg, title):
    """It raise a dialog. It a blocking function."""
    dialog = Gtk.MessageDialog(parent, flags, type_, buttons, msg)
    dialog.set_title(title)
    dialog.run()
    dialog.destroy()


class SensorsListModel(object):
    """A TreeView showing the available sensors. It allows to
    add/edit/delete custom sensors."""

    def __init__(self, parent):

        self.ind_parent = parent
        self._list_store = Gtk.ListStore(str, str)
        self._tree_view = Gtk.TreeView(self._list_store)

        self.sensor_mgr = SensorManager()
        self.sensor_mgr.fill_liststore(self._list_store)

    def get_view(self):
        """It's called from Preference. It creates the view and returns it"""
        vbox = Gtk.VBox(False, 3)
        # create columns
        renderer = Gtk.CellRendererText()
        renderer.set_property('editable', False)
        column = Gtk.TreeViewColumn(_('Sensor'), renderer, text=0)
        self._tree_view.append_column(column)

        renderer = Gtk.CellRendererText()
        renderer.set_property('editable', False)
        column = Gtk.TreeViewColumn(_('Description'), renderer, text=1)
        self._tree_view.append_column(column)

        self._tree_view.expand_all()
        sw = Gtk.ScrolledWindow()
        sw.add_with_viewport(self._tree_view)
        vbox.pack_start(sw, True, True, 0)

        # add buttons
        hbox = Gtk.HBox()
        new_button = Gtk.Button.new_from_stock(Gtk.STOCK_NEW)
        new_button.connect('clicked', self._on_edit_sensor)
        hbox.pack_start(new_button, False, False, 0)

        edit_button = Gtk.Button.new_from_stock(Gtk.STOCK_EDIT)
        edit_button.connect('clicked', self._on_edit_sensor, False)
        hbox.pack_start(edit_button, False, False, 1)

        del_button = Gtk.Button.new_from_stock(Gtk.STOCK_DELETE)
        del_button.connect('clicked', self._on_del_sensor)
        hbox.pack_start(del_button, False, False, 2)

        add_button = Gtk.Button.new_from_stock(Gtk.STOCK_ADD)
        add_button.connect('clicked', self._on_add_sensor)
        hbox.pack_end(add_button, False, False, 3)
        vbox.pack_end(hbox, False, False, 1)

        frame = Gtk.Frame.new(_('Sensors'))
        frame.add(vbox)
        return frame

    def _get_selected_row(self):
        """Returns an iter for the selected rows in the view or None."""
        model, pathlist = self._tree_view.get_selection().get_selected_rows()
        if len(pathlist):
            path = pathlist.pop()
            return model.get_iter(path)
        return None

    def _on_add_sensor(self, evnt=None, data=None):
        tree_iter = self._get_selected_row()
        if tree_iter is None:
            return

        sensor = self._list_store.get_value(tree_iter, 0)
        self.ind_parent.custom_entry.insert_text("{{{}}}".format(sensor), -1)

    def _on_edit_sensor(self, evnt=None, blank=True):
        """Raises a dialog with a form to add/edit a sensor"""
        name = desc = cmd = ""
        tree_iter = None
        if not blank:
            # edit, so get the info from the selected row
            tree_iter = self._get_selected_row()
            if tree_iter is None:
                return

            name = self._list_store.get_value(tree_iter, 0)
            desc = self._list_store.get_value(tree_iter, 1)
            cmd = self.sensor_mgr.get_command(name)

            if cmd is True:  # default sensor
                raise_dialog(
                    self.ind_parent, Gtk.DialogFlags.DESTROY_WITH_PARENT
                    | Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
                    Gtk.ButtonsType.OK, _("Can not edit the default sensors."),
                    _("Error"))
                return

        dialog = Gtk.Dialog(
            _("Edit Sensor"), self.ind_parent,
            Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.REJECT, Gtk.STOCK_OK,
             Gtk.ResponseType.ACCEPT))
        vbox = dialog.get_content_area()

        hbox = Gtk.HBox()
        label = Gtk.Label(_("Sensor"))
        sensor_entry = Gtk.Entry()
        sensor_entry.set_text(name)
        hbox.pack_start(label, False, False, 0)
        hbox.pack_end(sensor_entry, False, False, 1)
        vbox.pack_start(hbox, False, False, 0)

        hbox = Gtk.HBox()
        label = Gtk.Label(_("Description"))
        desc_entry = Gtk.Entry()
        desc_entry.set_text(desc)
        hbox.pack_start(label, False, False, 0)
        hbox.pack_end(desc_entry, False, False, 1)
        vbox.pack_start(hbox, False, False, 1)

        hbox = Gtk.HBox()
        label = Gtk.Label(_("Command"))
        cmd_entry = Gtk.Entry()

        cmd_entry.set_text(cmd)
        hbox.pack_start(label, False, False, 0)
        hbox.pack_end(cmd_entry, False, False, 1)
        vbox.pack_end(hbox, False, False, 2)

        dialog.show_all()
        response = dialog.run()

        if response == Gtk.ResponseType.ACCEPT:
            try:
                newname, desc, cmd = str(sensor_entry.get_text()), \
                                     str(desc_entry.get_text()), str(cmd_entry.get_text())

                if blank:
                    self.sensor_mgr.add(newname, desc, cmd)
                else:
                    self.sensor_mgr.edit(name, newname, desc, cmd)
                    self._list_store.remove(tree_iter)

                self._list_store.append([newname, desc])
                # issue 3: why we are doing a character replacement when clicking
                # new - who knows ... lets just comment this out
                # ctext = self.ind_parent.custom_entry.get_text()

                # self.ind_parent.custom_entry.set_text(
                #    ctext.replace(name, newname))

            except ISMError as ex:
                raise_dialog(
                    self.ind_parent, Gtk.DialogFlags.DESTROY_WITH_PARENT
                    | Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
                    Gtk.ButtonsType.OK, ex, _("Error"))

        dialog.destroy()

    def _on_del_sensor(self, evnt=None, data=None):
        """Remove a custom sensor."""
        tree_iter = self._get_selected_row()
        if tree_iter is None:
            return

        name = self._list_store.get_value(tree_iter, 0)
        try:
            self.sensor_mgr.delete(name)
            self._list_store.remove(tree_iter)
            ctext = self.ind_parent.custom_entry.get_text()
            self.ind_parent.custom_entry.set_text(
                ctext.replace("{{{}}}".format(name), ""))

        except ISMError as ex:
            raise_dialog(
                self.ind_parent,
                Gtk.DialogFlags.DESTROY_WITH_PARENT | Gtk.DialogFlags.MODAL,
                Gtk.MessageType.ERROR, Gtk.ButtonsType.OK, ex, _("Error"))


class Preferences(Gtk.ApplicationWindow):
    """It define the the Preferences Dialog and its operations."""

    sensors_regex = re.compile("{.+?}")

    SETTINGS_FILE = DIR_CONFIG + '/preferences_sm.json'
    settings = {}

    def __init__(self, parent, ind_parent):
        """It creates the widget of the dialogs"""
        Gtk.Window.__init__(self)
        self.set_border_width(10)
        self.set_size_request(600, 600)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_keep_above(True)
        self.set_title("监测设置")

        self.ind_parent = ind_parent
        self.custom_entry = None
        self.interval_entry = None
        self.sensor_mgr = SensorManager()
        self._create_content()
        self.set_data()
        self.show_all()

    def _create_content(self):
        ui = Gtk.Builder()
        ui.add_from_file('./preferences_sm.ui')

        self.custom_entry = ui.get_object('custom_entry')
        self.interval_entry = ui.get_object('interval_entry')

        sensors_list = SensorsListModel(self)
        vbox = ui.get_object('advanced_box')
        vbox.pack_start(sensors_list.get_view(), True, True, 0)

        ui.get_object('test_button').connect('clicked', self.on_test)
        ui.get_object('save_button').connect('clicked', self.on_save)
        ui.get_object('cancel_button').connect('clicked', self.on_cancel)

        self.add(vbox)
        self.set_resizable(False)

    def save_prefs(self):
        """It stores the current settings to the config file."""

        try:
            os.makedirs(os.path.dirname(Preferences.PREF_SETTINGS_FILE),
                        exist_ok=True)
            with open(Preferences.PREF_SETTINGS_FILE, 'w') as f:
                f.write(json.dumps(self.pref_settings))

        except Exception as ex:
            logging.exception(ex)
            logging.error('Writing settings failed')

    def load_settings(self):
        """It gets the settings from the config file and
            sets them to the correct vars"""
        try:
            with open(Preferences.PREF.SETTINGS_FILE, 'r') as f:
                self.settings = json.load(f)

        except Exception as ex:
            logging.exception(ex)
            logging.error('Reading settings failed')

    def on_iconpath_button_clicked(self, *args):
        pass

    def on_test(self, evnt=None, data=None):
        try:
            self.update_parent()
        except Exception as ex:
            error_dialog = Gtk.MessageDialog(
                None, Gtk.DialogFlags.DESTROY_WITH_PARENT,
                Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE, ex)
            error_dialog.set_title("Error")
            error_dialog.run()
            error_dialog.destroy()
            return False

    def on_save(self, evnt=None, data=None):
        """The action of the save button."""
        try:
            self.update_parent()
        except Exception as ex:
            error_dialog = Gtk.MessageDialog(
                None, Gtk.DialogFlags.DESTROY_WITH_PARENT,
                Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE, ex)
            error_dialog.set_title("Error")
            error_dialog.run()
            error_dialog.destroy()
            return False

        self.ind_parent.save_settings()

        self.destroy()

    def on_cancel(self, evnt=None, data=None):
        """The action of the cancel button."""
        self.ind_parent.load_settings()
        self.destroy()

    def update_parent(self, evnt=None, data=None):
        custom_text = self.custom_entry.get_text()

        sensors = Preferences.sensors_regex.findall(custom_text)
        for sensor in sensors:
            sensor = sensor[1:-1]
            if not self.sensor_mgr.exists(sensor):
                raise ISMError(
                    _("{{{}}} sensor not supported.").format(sensor))
            self.sensor_mgr.check(sensor)

        try:
            interval = float(self.interval_entry.get_text())
            if interval < 1:
                raise ISMError(
                    _("Interval value should be greater then or equal to 1 "))

        except ValueError:
            raise ISMError(_("Interval value is not valid."))

        self.sensor_mgr.set_custom_text(custom_text)
        self.sensor_mgr.set_interval(interval)
        self.ind_parent.update_settings()
        self.ind_parent.update_indicator_guide()

    def set_data(self):
        """It sets the widgets with the config data."""
        self.custom_entry.set_text(self.sensor_mgr.get_custom_text())
        self.interval_entry.set_text(str(self.sensor_mgr.get_interval()))
