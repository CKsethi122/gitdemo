"""
# Test Case Name           : STORELIB -GetControllerInfo
# Test Case Number         : SCGCQ00532910
# Creation Date            : 24/08/2015
# Test Script Author       : Siva<siva-sankar-reddy.basireddy@avagotech.com>
# H/W requirements         : a. Enclosures required: One enclosure and
#                                one backplane (connect jbod with some pds)
#                            b. Applicable Controllers  : All
#
#                            c. OS Support : Windows / Linux
#                            d. Disks required: 4
# Expected Run time        : 2
# Test Script usage Notes  : a. To run this test case, kindly provide input
#                 parameter as python <TC_name>.py --ctrl=<ctrl_index> --nocq
#
# Test Script usage Notes  : Flash Controller firmware using SLT.
# Windows:  python SCGCQ00541788.py --ctrl=<ctrl-indx>
            --new_fw_path="C:\Users\Administrator\Desktop\Pavan\MR_4MB.rom" --nocq
#
# Linux:  # python SCGCQ00541788.py --ctrl=<ctrl-indx>
            --new_fw_path='/root/Desktop/siva/1808/MR_4MB.rom' --nocq
#
# TestCaseName: STORELIB -GetControllerInfo
Description: Verify controller information
 -----------------------------------------------------------------------------
 Step Number: 1
 Step Details: -flash new firmware <BR>-connect some drives to the controller
 w/o enclosure
 <BR>-create some logical drives
 Step Expected Result: -Should get new Firmware version, bios version...etc.
 <BR>-Should get VendorID, SubSystemID...
 <BR>-Should print the product name info <BR>-Should get #PD present,
 #PD critical, #PD offline
 <BR>-Should get number of LD present, #LD critical, #LD failed <BR>-Alarm,
 data transfer rate
 <BR>-Memory size, <BR>-Cluster info, <BR>-Raid support,
 <BR> Support adapter option, <BR>-Support SAS and SATA mix....
 <BR>-Rebuild rate, CC rate, INIT rate, Reconstruction rate....etc
 -----------------------------------------------------------------------------
 Step Number: 2
 Step Details: -Connect an enclousre with some drives within enclosure.
 Issue GetControllerInfo
 Step Expected Result: -should display device ID of enclosure
 <BR>-SAS address
 <BR>-should display what ID within enclosure....
 -----------------------------------------------------------------------------
"""

import time

from sal.mradapter import create_mradapter
from sal.testscript import TestScript, arg
from sal.storelib_defines import KB, GB
from sal.common import SALError


class SalTestCase(TestScript):

    """STORELIB -GetControllerInfo"""
    REQ_ARGS = [arg("--ctrl", dest="ctrl", type="int", help="ctrl ID number"),
                arg("--new_fw_path", dest="new_fw_path", type="str",
                    help="New Firmware Path")]

    def init(self):
        """ create mr adapter instance"""
        self.mr = create_mradapter(ctrl_index=self.args.ctrl, test_script=self)
        # make sure that OCR to be enabled on the controller
        if ('ON' in self.mr.cli.ocr_get()):
            self.log.info("OCR Already enabled")
        else:
            self.mr.cli.ocr_set(setting="ON")
            self.log.info("OCR State changed to ON")

    def teardown(self):
        """ Clean up VDs and PDs on a failure """
        self.mr.restore_pretest(pretest=self.pretest_info)

    def step1(self):
        """Connect some drives to the controller w/o enclosure
        <BR>-create some logical drives
        Step Expected Result: -Should get new Firmware version, bios version...etc.
        <BR>-Should get VendorID, SubSystemID...
        <BR>-Should print the product name info
        <BR>-Should get #PD present, #PD critical, #PD offline
        <BR>-Should get number of LD present, #LD critical, #LD failed
        <BR>-Alarm, data transfer rate
        <BR>-Memory size <BR>-Cluster info <BR>-Raid support <BR>-Support adapter option
        <BR>-Support SAS and SATA mix....
        <BR>-Rebuild rate, CC rate, INIT rate, Reconstruction rate....etc"""
        int_fw_val = self.mr.firmware_version
        self.log.info("Current FW version: %s" % int_fw_val)
        self.log.info("Flashing firmware: %s" % (self.args.new_fw_path))
        self.mr.flash_file(firmware_filename=self.args.new_fw_path)
        time.sleep(240)  # sleep for 4m
        post_fw_val = self.mr.firmware_version
        if int_fw_val == post_fw_val:
            raise SALError("Failed to change firmware version!")
        else:
            self.log.info("FW  Flashed successfully")
            self.log.info("New FW version: %s" % post_fw_val)

        # get controller properties from sl and cli
        ctrl_prop_sl = self.mr.get_ctrl_property()
        ctrl_prop_cli = self.mr.cli.get_all()

        if ctrl_prop_sl['BIOS'].upper() != ctrl_prop_cli['bios_version'].upper():
            raise SALError("Failed to match bios_version!")
        else:
            self.log.info("bios_version: %s" % ctrl_prop_sl['BIOS'])

        drv_info = self.mr.get_driver_version()  # get driver info from sl
        if drv_info['version'].strip() != ctrl_prop_cli['driver_version']:
            raise SALError("Failed to match driver_version!")
        else:
            self.log.info("driver_version: %s" % drv_info['version'].strip())

        if drv_info['name'].upper() != ctrl_prop_cli['driver_name'].upper():
            raise SALError("Failed to match driver_name!")
        else:
            self.log.info("driver_name: %s" % drv_info['name'])

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

        self.log.info("alarmEnable: %s" % ctrl_prop_sl['alarmEnable'])
        self.log.info("memorySize: %s" % ctrl_prop_sl['memorySize'])
        self.log.info("max_data_transfer_size: %s" %
                      ctrl_prop_cli['max_data_transfer_size'])

        # get pds from back plane, connect only one enclosure and one back
        # plane
        encl_ids_sl = self.mr.get_encls()
        pds = self.mr.get_all_pds(state='unconfigured_good')
        pds_bp = [pd for pd in pds if pd.get_info()['enclDeviceId'] !=
                  str(encl_ids_sl[0])]
        if len(pds_bp) == 0:
            raise SALError("No PDs found on backplane")
        else:
            self.log.info("PD's count on backplane: %d" % len(pds_bp))
        self.vds = self.mr.add_vd(raid=0, absolute_space="10GB",
                                  pd_list=pds_bp, vd_count=2)
        for vd in self.vds:
            while vd.fgi_running:
                time.sleep(6)  # fgi is still running, sleep for 6 sec
        for vd in self.vds:
            if vd.get_state() != 3:  # Optimal
                raise SALError("The VD failed to be created optimal!")
            else:
                self.log.info("Raid %s VD: %d created." %
                              (vd.raid_level, vd.id))

        ctrl_health = self.mr.get_ctrl_health()
        self.log.info("*****Display PD health*****")
        self.log.info("pdOptimalCount:%d" % ctrl_health['pdOptimalCount'])
        self.log.info("pdPredFailCount: %d"
                      % ctrl_health['pdPredFailCount'])
        self.log.info("pdFailedCount: %d"
                      % ctrl_health['pdFailedCount'])

        self.log.info("*****Display LD health*****")
        if ctrl_health['ldOptimalCount'] != 2:
            raise SALError("ldOptimalCount is not matching")
        else:
            self.log.info("ldOptimalCount: %d" %
                          ctrl_health['ldOptimalCount'])

        if ctrl_health['ldCriticalCount'] != 0:
            raise SALError("ldCriticalCount is not matching")
        else:
            self.log.info("ldCriticalCount: %d" %
                          ctrl_health['ldCriticalCount'])
        if ctrl_health['ldOfflineCount'] != 0:
            raise SALError("ldOfflineCount is not matching")
        else:
            self.log.info("ldOfflineCount: %d" %
                          ctrl_health['ldOfflineCount'])

        # Display the cluster information
        self.log.info("*****Display cluster information*****")
        cluster_info = self.mr.get_controller_capabilities(
            group_name='cluster')
        for k, v in iter(sorted(cluster_info.iteritems())):
            self.log.info("%s : %s" % (k, v))

        rl_s = self.mr.get_controller_capabilities(group_name='raidLevels')
        for k, v in iter(sorted(rl_s.iteritems())):
            self.log.info("%s : %s" % (k, v))

        self.log.info("*****Display adapter operation information*****")
        adp_op = self.mr.get_controller_capabilities(
            group_name='adapterOperations')
        for k, v in iter(sorted(adp_op.iteritems())):
            self.log.info("%s : %s" % (k, v))

        self.log.info("*****Display pd/ld mix information*****")
        pd_mix = self.mr.get_controller_capabilities(group_name='pdMixSupport')
        for k, v in iter(sorted(pd_mix.iteritems())):
            self.log.info("%s : %s" % (k, v))

        self.log.info("*****Display Rates information*****")
        rates_sl = ['bgiRate', 'ccRate', 'patrolReadRate', 'rebuildRate',
                    'reconRate']
        rates_cl = ['bgi_rate_current', 'check_consistency_rate_current',
                    'pr_rate_current', 'rebuild_rate_current',
                    'reconstruction_rate_current']
        for (key1, key2) in zip(rates_sl, rates_cl):
            if str(ctrl_prop_sl[key1]) != ctrl_prop_cli[key2]:
                raise SALError("Failed to match %s" % key1)
            else:
                self.log.info("%s: %d" % (key1, ctrl_prop_sl[key1]))

    def step2(self):
        """ Connect an enclosure with some drives within enclosure.
        Issue GetControllerInfo should display device ID of enclosure
        <BR>-SAS address
        <BR>-should display what ID within enclosure.... """

        encls_ids_sl = self.mr.get_encls()
        encl_list = self. mr.get_encl_list()
        # encls_ids_cli = self.mr.cli.enclosure_list()

        if encls_ids_sl[0] != encl_list['encl0_deviceId']:
            raise SALError("Failed to match enclosure ID!")
        else:
            self.log.info("Enclosure ID: %d" % encls_ids_sl[0])
        ctrl_prop_cli = self.mr.cli.get_all()  # get controller properties through cli
        self.log.info("sas_address: %s" % ctrl_prop_cli['sas_address'])
        pds = self.mr.get_all_pds(encl_id=encls_ids_sl[0])
        for pd in pds:
            pd_c = pd.get_info()['enclDeviceId'] + ':' + str(pd.slotNumber)
            info = self.mr.cli.pd_get_info(pd_string=pd_c)
            pd_size1 = int(int(info['size']) / KB)  # convert MB into GB
            pd_size2 = int(pd.size / GB)  # convert pd size bytes into GB
            size = abs(pd_size1 - pd_size2)  # get absolute value
            if size > 2:  # if size difference more than 2GB raise salerror
                raise SALError("Failed to match PD size!")
            else:
                self.log.info("PD size in GB: %d" % pd_size2)

            if info['media_type'] != pd.media_type.upper():
                raise SALError("Failed to match media_type!")
            else:
                self.log.info("PD: %s, Media type: %s" %
                              (pd_c, info['media_type']))

            if info['media_error_count'] != pd.get_info()['mediaErrCount']:
                raise SALError("Failed to match mediaErrCount!")
            else:
                self.log.info("PD: %s, mediaErrCount: %s " %
                              (pd_c, info['media_error_count']))
            if info['firmware_revision'] != pd.get_info()['revisionLevel']:
                raise SALError("Failed to match firmwware_revision!")
            else:
                self.log.info("PD: %s, firmware_revision: %s " %
                              (pd_c, info['firmware_revision']))
            sas_add_sl = pd.unique_id.split(':')[-1]
            if len(info['sas_address_0']) > 3:
                sas_add_cli = info['sas_address_0'].replace('0X', '')
                i = 0
            else:
                sas_add_cli = info['sas_address_1'].replace('0X', '')
                i = 1
            if sas_add_cli != sas_add_sl:
                raise SALError("Failed to match SAS address")
            else:
                self.log.info("PD: %s, sas_address_%s: 0X%s" %
                              (pd_c, i, sas_add_cli))
            if self.mr.cli.pd_is_sas(pd_string=pd_c):  # if pd is SATA skip
                if len(info['sas_address_0']) > 3:
                    self.log.info("PD: %s, sas_address_1: %s" %
                                  (pd_c, info['sas_address_1']))
                else:
                    self.log.info("PD: %s, sas_address_0: %s" %
                                  (pd_c, info['sas_address_0']))

        self.log.info("Delete the above created VD")
        for vd in self.vds:
            vd.delete()


if __name__ == '__main__':
    SalTestCase().run()
