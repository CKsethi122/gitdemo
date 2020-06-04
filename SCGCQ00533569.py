"""
    # Test Case Name           :  CLI - Display/Change adapter boot drive.
    # Test Case Number         : SCGCQ00533569
    # Creation Date            : 25/08/2015
    # Test Script Author       : Pavan Kumar
    # Modification Date        : 30/11/2015
    # Pre-requisite            : a. Disks required : 10  SAS HDD's.
    #                               on each controller.
    #                            b. Controllers: All MR Cards
    #                             (MR Invader, MR Liberator, MR TB).
    #                            c. OS Support : Windows / Linux.
    # Expected Run time        : 20 minutes
    # Test Script usage Notes  : python ate2run.py SCGCQ00533569.py
    Note 1: Install latest ATE and modify ate2cgf.txt by modifying
    script arguments such as --ctrl, --nocq, --noftp, --block_ctrl and then
    run again python ate2run.py SCGCQ00533569.py.
    Note:You could pass in an optional parameter
            "--block_ctrl" to prevent a selcted controller from being
            used in the rare config that you have a controller that
            you will not be testing on(boot up PD only).
            Ex: --block_ctrl="1,2" then controllers 1 and 2 will not be
            used for test execution.
    Press "Y" to start script execution using ATE.
    To query script status use: python ate2cli.py -s 127.0.0.1 -l

TestCaseName: BST-  CLI - Display/Change adapter boot drive.
Description: Verify functionality of boot drive change..

Step Number: 1
Step Details: Restore Factory Defaults
Step Expected Result: Sets the controller settings back to the factory set
                      defaults.

Step Number: 2
Step Details: Create multiple logical drives of different RAID levels with
              different properties
Step Expected Result: Multiple logical drives created without errors

Step Number: 3
Step Details: Display the cache flush time  of each controller one at a time
Step Expected Result: Cache flush time shows correct according to the last
      one set by the user.  If not set, should show the controller default.

Step Number: 4
Step Details: Display the boot drive of each controller one at a time
Step Expected Result: Boot drive shows correct according to the last one set
              by the user.  If not set, should show the controller default.

Step Number: 5
Step Details: Reboot system
Step Expected Result: System reboots without error

Step Number: 6
Step Details: Display the boot drive for all of the controllers at
              once(using -a0,1,2 format)
Step Expected Result: All boot drives show correctly.

Step Number: 7
Step Details: Set the boot drive on all controllers at once (-aALL)
Step Expected Result: All controllers boot drives change and the data is saved
                     to the controller.

Step Number: 8
Step Details: Display the boot drive for all of the controllers at once (-aALL)
Step Expected Result: All boot drives show correctly.
"""

import time
import sal.util

from sal.testscript import TestScript, arg
from sal.mradapter import create_mradapter
from sal.common import SALError


class SalTestCase(TestScript):
    """ Verify functionality of boot drive change"""
    REQ_ARGS = [arg("--ctrl", dest="ctrl", type="int",
                    help="Controller index")]
    OPT_ARGS = [arg("--block_ctrl", dest="block_ctrl", type="str",
                    help="List of Block Controller list seperated by comma")]

    def init(self):
        """ create mr adapter instance"""
        self.mrs = []
        if self.args.block_ctrl is not None:
            self.block_ctrl_list = self.args.block_ctrl.split(",")
            # Verify User input as per 0,1,2 format.
            if "" in self.block_ctrl_list:
                raise SALError("Invalid Input:[%s] to block controller "
                               "arguments given to scripts!!!"
                               % (self.block_ctrl_list))
        else:
            self.block_ctrl_list = ""
        # Create MR instance for controller index using --ctrl input.
        self.mrs.append(create_mradapter(ctrl_index=self.args.ctrl))
        self.ctrl_cnt = self.mrs[0].cli.controller_count()
        for index in range(0, self.ctrl_cnt):
            # Check for Block controller list.
            if str(index) not in self.block_ctrl_list:
                # Check for --Ctrl index given as arg to script.
                if index != self.args.ctrl:
                    self.log.info("Creating MR instance for Controller-%d"
                                  % (index))
                    self.mrs.append(create_mradapter(ctrl_index=index))
            else:
                self.log.info("*****TC will not execute on Blocked "
                              "Controller-%d*****" % (index))
        for mr in self.mrs:
            if not mr.is_mr():
                raise SALError("This script is applicable only for MR "
                               "controller cards")

    def teardown(self):
        """ Clean up in case of failure """
        for mr in self.mrs:
            mr.restore_pretest(pretest=mr.pretest_info)

    def step1(self):
        """ Restore Factory Defaults"""
        self.set_value = 35
        self.default_value = 30
        self.log.info("Set CC Rate to 35 on all controllers")
        for mr in self.mrs:
            self.log.info("Set CC Rate on controller: %d", mr.ctrl_id)
            mr.cli.ccrate_set(self.set_value)
        init_val = []
        for mr in self.mrs:
            init_val.append(mr.cli.ccrate_get())
        self.log.info("Verify new CC Rate val on all controller")
        for (id, val) in enumerate(init_val):
            if val != self.set_value:
                raise SALError("CC Rate not set right on controller")
            else:
                self.log.info("Verified CC Rate on Controller: %d : %d"
                              % (id, val))
        self.log.info("Set to factory defaults on all controllers")
        for mr in self.mrs:
            self.log.info("Set to factory defaults on controller: %d, wait "
                          "for 250 secs" % (mr.ctrl_id))
            mr.cli.factory_defaults_set(restart=True)
            time.sleep(250)
        post_val = []
        for mr in self.mrs:
            post_val.append(mr.cli.ccrate_get())
        self.log.info("Verify CC Rate val on all controller after "
                      "factory defaults")
        for (id, val) in enumerate(post_val):
            if val != self.default_value:
                raise SALError("Failed to reset CC Rate on controller")
            else:
                self.log.info("Verified CC Rate reset on Controller: %d : %d"
                              % (id, val))

    def step2(self):
        """ Create multiple logical drives of different RAID levels with
            different properties"""
        self.mr_vds = []
        # Checking UGood availablity here, because after reboot cycle,
        # init will be called.
        for mr in self.mrs:
            self.log.info("Check for UGood PD's availablity on controller:%d"
                          % (mr.ctrl_id))
            pds = mr.cli.list_all_drives(pd_type="SAS",
                                         state="UGood", media_type="HDD",
                                         sector_size='512B')
            if len(pds) < 10:
                raise SALError("%d UGood HDD PD's are not available for RAID "
                               "Creation on Controller:%d"
                               % (10 - len(pds), mr.ctrl_id))
            else:
                self.log.info("Number of UGood HDD PD's available is %d on "
                              "controller:%d" % (len(pds), mr.ctrl_id))
        for mr in self.mrs:
            self.vds = []
            self.log.info("Create R0, R1, R5 with diff properties on "
                          "Controller: %d" % (mr.ctrl_id))
            self.vds.append(mr.cli.add_vd(raid=0, vd_size="3000MB",
                                          WB="WB", RA='ra', cache="direct"))
            self.vds.append(mr.cli.add_vd(raid=1, vd_size="3000MB",
                                          WB="WT", RA='nora', cache="cached"))
            self.vds.append(mr.cli.add_vd(raid=5, vd_size="3000MB",
                                          WB="WB", RA='ra', cache="direct"))
            for vd in self.vds:
                while True:
                    time.sleep(5)
                    if (mr.cli.init_progress(vd) == -1):
                        self.log.info("FGI completed for VD:%s"
                                      % (vd))
                        break
            for vd in self.vds:
                if mr.cli.vd_get_info(vd)['state'] != 'OPTL':
                    raise SALError("RAID-%s VD%s is not optimal"
                                   % (mr.cli.vd_get_info(vd)['raid'], vd))
                else:
                    self.log.info("RAID-%s VD%s is optimal"
                                  % (mr.cli.vd_get_info(vd)['raid'], vd))

            self.mr_vds.extend(self.vds)
            self.log.info("Created R0, R1, R5 successfully on controller: %d"
                          % (mr.ctrl_id))

    def step3(self):
        """ Display the cache flush time  of each controller one at a time"""
        for mr in self.mrs:
            self.log.info("Cache Flush time of controller:%d is %d"
                          % (mr.ctrl_id, mr.cli.cacheflushint_get()))

    def step4(self):
        """ Display the boot drive of each controller one at a time"""
        for mr in self.mrs:
            self.log.info("Boot drive of controller: %d is %d"
                          % (mr.ctrl_id, mr.cli.bootdrive_vd_get()))

    def step5(self):
        """ Reboot system"""
        self.log.info("Server is going to reboot now")
        time.sleep(5)
        self.save_state(advance=True)
        sal.util.reboot_system()
        self.wait_for_restart()

    def step6(self):
        """ Display the boot drive for all of the controllers at
            once(using -a0,1,2 format)"""
        if len(self.mrs) == 3:
            count = 3
        elif len(self.mrs) == 2:
            count = 2
        else:
            count = 1
        for mr in self.mrs[0:count]:
            self.log.info("Display boot drive on controller:%d"
                          % (mr.ctrl_id))
            vd_id = mr.cli.bootdrive_vd_get()
            if (int(vd_id) == -1):     # -1 : No boot VD.
                self.log.info("No boot VD found on controller: %d"
                              % (mr.ctrl_id))
            else:
                self.log.info("VD ID of the boot VD: %d"
                              % int((vd_id)))

    def step7(self):
        """ Set the boot drive on all controllers at once (-aALL)"""
        for indx, mr in enumerate(self.mrs):
            self.log.info("Set boot drive on controller:%d"
                          % (mr.ctrl_id))
            for vd in self.mr_vds[indx]:
                if (int(mr.cli.bootdrive_vd_get()) != vd):
                    mr.cli.bootdrive_vd_set(vd_id=self.mr_vds[indx][indx],
                                            setting="On")
                    break

    def step8(self):
        """ Display the boot drive for all of the controllers at once
            (-aALL)"""
        for mr in self.mrs:
            self.log.info("Display boot drive on controller:%d"
                          % (mr.ctrl_id))
            vd_id = mr.cli.bootdrive_vd_get()
            if (int(vd_id) == -1):     # -1 : No boot VD.
                raise SALError("Failed to verify boot drive")
            else:
                self.log.info("Verified VD ID: %d of the boot VD on "
                              "controller: %d" % (int(vd_id), mr.ctrl_id))
        for vd in self.mr_vds:
            self.mrs[0].cli.delete_vd(vd_id=vd)
        time.sleep(30)
        self.log.info("Deleted all VD's succesfully")

if __name__ == '__main__':
    SalTestCase().run()
