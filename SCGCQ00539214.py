"""
# Test Case Name           : Verification of events for PD and LD related
#                            operations in Vivaldi and StoreLibTest
# Test Case Number         : SCGCQ00539214
# Creation Date            : 30/09/2015
# Test Script Author       : Siva<siva-sankar-reddy.basireddy@avagotech.com>
# Pre-requisites            :a. Enclosures required: One
#                            b. Applicable Controllers : All
#                            c. Disks required: 6
#               3 - SAS 512B drives.(3 connected through DTAB port 1, 2 and 3)
#               3 - SAS/SATA
#                            d. OS Support : Windows / Linux
# Expected Run time       : 30 minutes
# Note: 1) We are using storcli to cross verify SL things as required instead
# of MSM.
# 2) Don't put OS on VD since we are going to use clear_config() which will
#    delete all the VDs on the controller.
#
# Test Script usage Notes  : python SCGCQ00539214.py --ctrl=0 --nocq
#                               --quarch_ip=<quarch ip>
# parameter as #python SCGCQ00539214.py --ctrl=<ctrl_index> --nocq
#                                       --quarch_ip=<quarch-device-ip>
# Ex: #python SCGCQ00539214.py --ctrl=0 --nocq --quarch_ip="135.24.231.85"
#
# Note: Ping to quarch connector, connect 4 ribbon cable from quarch to
# PDs before starting the script.
#
# TestCaseName: Verification of events for PD and LD related operations in
 Vivaldi and StoreLibTest
 Description: (NO_VALUE)
 -----------------------------------------------------------------------------
 Step Number: 1
 Step Details: Log-in Vivaldi GUI. Open StoreLibTest as well.
 Step Expected Result: MSM should display the controller and its properties.
<BR>StoreLibTest also displays the controller. <BR>
 -----------------------------------------------------------------------------
 Step Number: 2
 Step Details: Connect 4 UnconfiguredGood PD"s to the Controller.
 Step Expected Result: StoreLibTest should show up events for the same.
 MSM monitor should throw events about PD"s been inserted and GUI should
 refresh on inserting the PD"s.
 -----------------------------------------------------------------------------
 Step Number: 3
 Step Details: Create a 2 drive R1 in MSM
 Step Expected Result: R1 is created without any error.Events related to it
 should be thrown in both MSM and StoreLibTest.
 -----------------------------------------------------------------------------
 Step Number: 4
 Step Details: Remove one of the PD"s from R1
 Step Expected Result: R1 should be shown as Degraded in MSM. .MSM monitor
 logs should display events for VD state change. StoreLibTest also should
 show up events for the State change of the VD.
 MSM GUI should also get refreshed
 -----------------------------------------------------------------------------
 Step Number: 5
 Step Details: Re-connect the PD
 Step Expected Result: PD should rebuild to completion. MSM and StoreLibTest
 should throw corresponding events.
 -----------------------------------------------------------------------------
 Step Number: 6
 Step Details: On Rebuild completion check for LD state change
 Step Expected Result:MSM should automatically refresh the State change of LD.
 Events related to same should be seen in both MSM and StoreLibTest.
 -----------------------------------------------------------------------------
 Step Number: 7
 Step Details: Assign an Unconfigured Good PD as a GlobalHotSpare
 Step Expected Result: GlobalHotSpare can be created without any hassles.
MSM monitor and StoreLibTest should show events for the same.
 -----------------------------------------------------------------------------
 Step Number: 8
 Step Details: Disconnect the PD assigned as GHS and reconnect the same
 Step Expected Result: Both the Events have to be displayed in MSM monitor and
 StoreLibTest. MSM GUI should also get refreshed.
 -----------------------------------------------------------------------------
 Step Number: 9
 Step Details: Clear the controller configuration and repeat the same for
 R1E volume
 Step Expected Result: StoreLibTest and hence MSM monitor should show up the
 event for the same.
 -----------------------------------------------------------------------------
 Step Number: 10
 Step Details: Disconnect all the 4 PDs
 Step Expected Result: MSM monitor logs should show up the events about the
 same and the GUI should get refreshed. StoreLibTest also should show up the
 PD removal events.
 -----------------------------------------------------------------------------
"""

import time

from sal.mradapter import create_mradapter
from sal.testscript import TestScript, arg
from sal import quarch, system
from sal.common import SALError
from sal.mraen import *


class SalTestCase(TestScript):

    """Verification of events for PD and LD related operations in Vivaldi and
    StoreLibTest"""
    REQ_ARGS = [arg("--ctrl", dest="ctrl", type="int", help="ctrl ID number"),
                arg("--quarch_ip", dest="quarch_ip", type="str",
                    help="Quarch IP address")]

    def init(self):
        """ create mr adapter instance"""
        self.mr = create_mradapter(ctrl_index=self.args.ctrl, test_script=self)

        self.raid = 1  # This will be used in step3
        self.pd_count = 1  # This will be used in step3

    def teardown(self):
        """ Clean up VDs and PDs on a failure """
        try:
            self.qrch = quarch.TorridonController(
                ip_address=self.args.quarch_ip)
            self.mod_list = self.qrch.get_modules()
            self.q_list = system.filter_devices(self.mod_list, type='dtab')
        except Exception:
            pass
        try:
            for dtab in self.q_list:  # Make sure all PDs are pushed in
                dtab.power(up=True)
                time.sleep(1)
            time.sleep(30)
            self.qrch.comm_obj.close()
        except Exception:
            pass

        self.mr.restore_pretest(pretest=self.pretest_info)

    def step1(self):
        '''Log-in Vivaldi GUI. Open StoreLibTest as well.
        MSM should display the controller and its properties.
        StoreLibTest also displays the controller.'''
        # enableEmergencySpare = 0
        # useGlobalSparesForEmergency = 0
        # useUnconfGoodForEmergency = 0
        # maintainPdFailHistory = 0
        self.mr.set_test_defaults()  # sets above properties to defaults
        self.mr.set_ctrl_property(restoreHotSpareOnInsertion=1)
        if self.mr.get_ctrl_property()['disableAutoRebuild'] == 1:
            self.mr.set_ctrl_property(disableAutoRebuild=0)
        time.sleep(30)  # sleep for 30sec
        if self.mr.get_ctrl_property()['disableAutoRebuild'] != 0:
            raise SALError("'disableAutoRebuild' is set to 1")
        else:
            self.log.info("'disableAutoRebuild' is set to 0")

        # get controller properties from sl and cli
        ctrl_prop_sl = self.mr.get_ctrl_property()
        ctrl_prop_cli = self.mr.cli.get_all()

        if ctrl_prop_sl['BIOS'].upper() != ctrl_prop_cli['bios_version'].upper():
            raise SALError("Failed to match bios_version!")
        else:
            self.log.info("bios_version: %s" % ctrl_prop_sl['BIOS'])

        keys_sl = ['pci_subDevId', 'pci_subVendorId', 'pci_vendorId']
        keys_cli = ['subdevice_id', 'subvendor_id', 'vendor_id']

        self.log.info("*****Display details about devieID, etc*****")
        for (key1, key2) in zip(keys_sl, keys_cli):
            # convert hex to decimal and then str to compare with SL values
            if ctrl_prop_sl[key1] != str(int(ctrl_prop_cli[key2], 16)):
                raise SALError("Failed to match %s" % key1)
            else:
                self.log.info("%s : %s" % (key1, ctrl_prop_sl[key1]))

        if ctrl_prop_sl['productName'].upper() != ctrl_prop_cli['model'].upper():
            raise SALError("Failed to match product name!")
        else:
            self.log.info("Product name: %s" % ctrl_prop_sl['productName'])

        self.log.info("*****Display full controller info*****")
        for key, val in iter(sorted(ctrl_prop_sl.iteritems())):
            self.log.info("%s <====> %s" % (key, val))

    def step2(self):
        '''Step Details: Connect 4 UnconfiguredGood PD"s to the Controller.
        Step Expected Result: StoreLibTest should show up events for the same.
        MSM monitor should throw events about PD"s been inserted and GUI should
        refresh on inserting the PD"s.'''
        proc_pd_insert = self.mr.wait_for_event(
            event_id=MR_EVT_PD_INSERTED, background=True)
        time.sleep(6)  # sleep for 6 sec
        self.qrch = quarch.TorridonController(ip_address=self.args.quarch_ip)
        self.mod_list = self.qrch.get_modules()
        self.q_list = system.filter_devices(self.mod_list, type='dtab')

        # Make sure all PDs are pushed out
        for dtab in self.q_list:
            dtab.power(up=False)
            time.sleep(1)
        time.sleep(30)

        # Make sure all PDs are pushed in
        for dtab in self.q_list:
            dtab.power(up=True)
            time.sleep(1)
        time.sleep(30)

        if proc_pd_insert.is_alive():  # check for pds insert aen
            raise SALError("AEN for PDs insert was not found")
        else:
            self.log.info("AEN for PDs insert was found")

    def step3(self):
        """R1 is created without any error. Events related to it should be
        thrown in both MSM and StoreLibTest"""
        proc_create = self.mr.wait_for_event(
            event_id=MR_EVT_LD_CREATED, background=True)
        proc_optimal = self.mr.wait_for_event(
            event_id=MR_EVT_LD_OPTIMAL, background=True)
        proc_init = self.mr.wait_for_event(
            event_id=MR_EVT_LD_INIT_SUCCESSFUL, background=True)
        proc_state = self.mr.wait_for_event(
            event_id=MR_EVT_PD_STATE_CHANGE, background=True)
        time.sleep(30)  # sleep for 30 sec

        # Drive group 1
        self.q_list[0].power(up=False)
        time.sleep(10)
        dg1 = self.mr.get_pds(pd_count=self.pd_count, is_sas=True)
        pds_after_pull = self.mr.get_all_pds()
        self.q_list[0].power(up=True)
        time.sleep(30)
        all_pds = self.mr.get_all_pds()
        for pd in all_pds:
            for after_pd in pds_after_pull:
                if pd.id == after_pd.id:
                    break
            else:
                break  # Found
        self.pd = pd  # will be used in step5
        dg1.append(pd)
        self.vd = self.mr.add_vd(
            raid=self.raid, pd_list=dg1, absolute_space="25GB", init_state=1)

        for _ in xrange(24):  # wait for 2m for aen, if not raise Error
            if proc_create.is_alive():  # check for vd create aen
                time.sleep(5)
            else:
                self.log.info("AEN for VD created found")
                self.log.info("VD ID: %d, raid: %s" %
                              (self.vd.id, self.vd.raid_level))
                break  # break if aen found
        else:
            proc_optimal.terminate()
            raise SALError("AEN for VD created was not found")
        time.sleep(15)  # sleep for 15 sec

        for _ in xrange(24):  # wait for 2m for aen, if not raise Error
            if proc_init.is_alive():  # check for init complete aen
                time.sleep(5)
            else:
                self.log.info("AEN for VD fast init found")
                break  # break if aen found
        else:
            raise SALError("AEN for VD fast init successful was not found")

        if proc_state.is_alive():  # check for pd state change aen
            raise SALError("AEN for PD state change was not found")
        else:
            self.log.info("AEN for PD state change is found")

        if proc_optimal.is_alive():  # check VD state optimal aen
            proc_create.terminate()
            raise SALError("AEN for VD optimal was not found")
        else:
            self.log.info("AEN for VD optimal found")

        # cross checking with storcli...
        if self.mr.cli.vd_get_info(self.vd.id)['state'] != 'OPTL':
            raise SALError("VD is not optimal")
        else:
            self.log.info("VD:%s is optimal" % (self.vd.id))

    def step4(self):
        """ Step Details: Remove one of the PD's from R1
        Expected Result: R1 should be shown as Degraded in MSM. MSM monitor
        logs should display events for VD state change.StoreLibTest also should
        show up events for the State change of the VD.
        MSM GUI should also get refreshed
        """
        self.proc_state = self.mr.wait_for_event(
            event_id=MR_EVT_PD_STATE_CHANGE, background=True)
        self.proc_deg = self.mr.wait_for_event(
            event_id=MR_EVT_LD_DEGRADED, background=True)
        time.sleep(12)
        self.q_list[0].power(up=False)  # Pull out one of the PD from R1
        time.sleep(10)

        if self.proc_deg.is_alive():  # check for VD degrade aen
            raise SALError("AEN for VD degrade was not found")
        else:
            self.log.info("AEN for VD degrade was found")

        if self.proc_state.is_alive():  # check for pd state change aen
            raise SALError("AEN for PD state change was not found")
        else:
            self.log.info("AEN for PD state change is found")

        # cross checking with storcli...
        if self.mr.cli.vd_get_info(self.vd.id)['state'] != 'DGRD':
            raise SALError("VD is not Degraded as it should be")
        else:
            self.log.info("VD:%s is Degraded" % (self.vd.id))

    def step5(self):
        """ Step Details: Re-connect the PD
        Step Expected Result: PD should rebuild to completion.
        MSM and StoreLibTest should throw corresponding events.
        """
        self.proc_rbld = self.mr.wait_for_event(
            event_id=MR_EVT_PD_RBLD_START_AUTO, pd=self.pd, background=True)
        self.proc_rbld_dn = self.mr.wait_for_event(
            event_id=MR_EVT_PD_RBLD_DONE_PD, background=True)
        self.proc_optimal = self.mr.wait_for_event(
            event_id=MR_EVT_LD_OPTIMAL, background=True)
        time.sleep(20)  # sleep for 20 sec

        # Pull in the PD which was pulled out earlier
        self.q_list[0].power(up=True)
        time.sleep(10)
        if self.mr.scan_foreign_config() > 0:
            self.mr.clear_foreign_config()
            time.sleep(30)

        for _ in range(24):
            time.sleep(5)
            if self.pd.get_progress_rebuild() != -1:
                self.log.info("Rebuild kicks in automatically")
                break
        else:
            raise SALError("Rebuild do not kick in automatically!")

        # check rebuild started or not through cli
        pds = self.vd.get_pds()
        for (indx, pd) in enumerate(pds):
            if pd.id == self.pd.id:
                break  # Found vd_pd index
        else:
            raise SALError("Not found the VD_PD index")

        if self.mr.cli.rebuild_progress(vd_id=int(self.vd.id), vd_pd=indx) == -1:
            raise SALError("Failed to start rebuild!")
        else:
            self.log.info("Rebuild kicks in automatically")

        for _ in range(24):
            if self.proc_rbld.is_alive():  # check for rebuild start aen
                time.sleep(5)
            else:
                self.log.info("AEN for PD rebuild auto start was found.")
                break
        else:
            raise SALError("AEN for PD rebuild auto start wasn't found!")

        while True:  # Monitor rebuild progress
            prog = self.pd.get_progress_rebuild()
            if prog != -1:
                time.sleep(10)
                self.log.info("PD ID: %d, rebuild progress: %d"
                              % (self.pd.id, prog))
            else:
                self.log.info("Rebuild is completed successfully")
                break  # break from while when rebuild is done

        time.sleep(5)  # sleep for 5s
        # check rebuild done or not through cli
        if self.mr.cli.rebuild_progress(vd_id=int(self.vd.id), vd_pd=indx) != -1:
            raise SALError("Rebuild is not completed yet!")
        else:
            self.log.info("Rebuild is completed successfully")

        for _ in range(24):
            if self.proc_rbld_dn.is_alive():  # check for rebuild done aen
                time.sleep(5)
            else:
                self.log.info("AEN for PD rebuild done is found!")
                break
        else:
            raise SALError("AEN for PD rebuild done wasn't found!")

    def step6(self):
        '''Step Details: On Rebuild completion check for LD state change
        Expected Result:MSM should automatically refresh the State change of LD
        Events related to same should be seen in both MSM and StoreLibTest.'''

        if self.proc_optimal.is_alive():  # check VD state optimal aen
            raise SALError("AEN for VD optimal was not found")
        else:
            self.log.info("AEN for VD optimal found")

        # cross checking with storcli...
        if self.mr.cli.vd_get_info(self.vd.id)['state'] != 'OPTL':
            raise SALError("VD is not optimal")
        else:
            self.log.info("VD:%s is optimal" % (self.vd.id))

    def step7(self):
        '''Step Details: Assign an Unconfigured Good PD as a GlobalHotSpare
        Expected Result: GlobalHotSpare can be created without any hassles.
        MSM monitor and StoreLibTest should show events for the same.
        '''
        proc_ghs = self.mr.wait_for_event(
            event_id=MR_EVT_PD_SPARE_GLOBAL_CREATED, background=True)
        time.sleep(6)  # sleep for 6 sec
        self.q_list[1].power(up=False)
        time.sleep(10)
        pds_after_pull = self.mr.get_all_pds(state='unconfigured_good')
        self.q_list[1].power(up=True)
        time.sleep(30)
        all_pds = self.mr.get_all_pds(state='unconfigured_good')
        for pd in all_pds:
            for after_pd in pds_after_pull:
                if pd.id == after_pd.id:
                    break
            else:
                break  # Found
        self.pd_ghs = pd
        self.pd_ghs.make_hotspare()
        time.sleep(5)

        if self.pd_ghs.state != 'hot_spare':
            raise SALError("Failed to create GHS!")
        else:
            self.log.info("GHS created on PD:%s" % self.pd_ghs.id)

        if proc_ghs.is_alive():  # check ghs aen
            raise SALError("AEN for GHS created was not found")
        else:
            self.log.info("AEN for GHS created found")

        # cross checking with storcli...
        if self.mr.cli.pd_get_info(self.pd_ghs.cli)['state'] != "GHS":
            raise SALError("Failed to create GHS")
        else:
            self.log.info("GHS is created on PD: %s" % self.pd_ghs.cli)

    def step8(self):
        '''Step Details:Disconnect the PD assigned as GHS and reconnect the same
        Expected Result:Both the Events have to be displayed in MSM monitor and
        StoreLibTest. MSM GUI should also get refreshed.
        '''
        proc_state = self.mr.wait_for_event(
            event_id=MR_EVT_PD_STATE_CHANGE, background=True)
        proc_ghs = self.mr.wait_for_event(
            event_id=MR_EVT_PD_SPARE_GLOBAL_CREATED, background=True)
        time.sleep(12)  # sleep for 12 sec
        self.q_list[1].power(up=False)  # disconnect GHS PD
        time.sleep(10)

        if proc_state.is_alive():  # check ghs pd state aen
            raise SALError("AEN for PD state change was not found")
        else:
            self.log.info("AEN for PD state change found")

        self.q_list[1].power(up=True)  # reconnect the GHS PD
        time.sleep(20)

        if proc_ghs.is_alive():  # check ghs aen
            raise SALError("AEN for GHS created was not found")
        else:
            self.log.info("AEN for GHS created found")

    def step9(self):
        '''Step Details: Clear the controller configuration and repeat the same for
        R1E volume
        Expected Result: StoreLibTest and hence MSM monitor should show up the
        event for the same.
        '''
        proc_clear = self.mr.wait_for_event(
            event_id=MR_EVT_CFG_CLEARED, background=True)
        time.sleep(6)  # sleep for 6 sec
        self.mr.clear_config()  # clear the config
        time.sleep(5)
        if len(self.mr.get_vds()) != 0:
            raise SALError("Failed to clear the configuration!")
        else:
            self.log.info("Cleared the configuration successfully")

        for _ in xrange(120):  # wait for 10m for aen, if not raise Error
            if proc_clear.is_alive():  # check for clear config aen
                time.sleep(5)
            else:
                self.log.info("AEN for clear config was found")
                break  # break if aen found
        else:
            raise SALError("AEN for clear config was not found")

        self.raid = 11  # This will be used in step3
        self.pd_count = 3  # This will be used in step3
        self.log.info("Repeat steps 3 to 8 for R1E volume")
        self.step3()
        self.step4()
        self.step5()
        self.step6()
        self.step7()
        self.step8()

    def step10(self):
        '''Step Details: Disconnect all the 4 PD"s
        Step Expected Result: MSM monitor logs should show up the events about
        the same and the GUI should get refreshed. StoreLibTest also should
        show up the PD removal events.'''
        proc_pd_rem = self.mr.wait_for_event(
            event_id=MR_EVT_PD_REMOVED, background=True)
        time.sleep(6)  # sleep for 6 sec
        self.log.info("Delete the above created VD: %d" % self.vd.id)
        self.vd.delete()
        # Make sure all PDs are pushed out
        for dtab in self.q_list:
            dtab.power(up=False)
            time.sleep(1)
        time.sleep(30)

        if proc_pd_rem.is_alive():  # check PD state
            raise SALError("AEN for PDs removal was not found")
        else:
            self.log.info("AEN for PDs removal found")


if __name__ == '__main__':
    SalTestCase().run()
