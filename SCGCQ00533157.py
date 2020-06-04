"""
# Test Case Name           : STORELIB -GetPDOperationProgress
# Test Case Number         : SCGCQ00533157
# Creation Date            : 14/07/2015
# Test Script Author       :Siva<siva-sankar-reddy.basireddy@avagotech.com>
# Modified Date            : 09/12/2015
# Version                  : 0.1
# Tested using SAL         : '0.1510.1.0'
# Review fix Author        : Pavan Kumar
# Pre-requisite            : a. Disk required: 5 SAS HDD's.
#                            b. Applicable Controllers  : All
#                            c. OS Support : Windows / Linux
# Expected Run time        : 10 minutes
# Test Script usage Notes  : python SCGCQ00533157.py --ctrl=<ctrl_id>
#                                                    --nocq
# Test case Description    :
 TestCaseName: STORELIB -GetPDOperationProgress
Description: Gets the progress of ongoing operation on a physical
 -----------------------------------------------------------------------------
 Step Number: 1
 Step Details: -From Storelibtest\System Menu\RegisterAEN.  Select all events
  <BR>-Create a redundant array (e.g. RAID1 / RAID5).
 Step Expected Result: -Should have a pop up AEN's output <BR>-After create LD,
 should have an event LD created successfull <BR>Storelib's configuration
 should show correctly number of arrays
 -----------------------------------------------------------------------------
 Step Number: 2
 Step Details: From PD menu, issue a make drive off-line command
 Step Expected Result: -Should have an event print the PD online state to
 offline <BR>-Drive should be off-line.  -Array should be degraded
 -----------------------------------------------------------------------------
 Step Number: 3
 Step Details: From PD menu, execute rebuild command
 Step Expected Result: -Should have events PD rebuilding state <BR>-Rebuild(s)
  should start without errors
 -----------------------------------------------------------------------------
 Step Number: 4
 Step Details: From PD menu, issue Get PD Operation progress on rebuilding
 drive
 Step Expected Result: -Should have events rebuilding completed <BR>-
 The progress should update with percentage until it reachs 100%
 -----------------------------------------------------------------------------
"""

import time

from sal.mradapter import create_mradapter
from sal.testscript import TestScript, arg
from sal.common import SALError
from sal.mraen import (MR_EVT_LD_CREATED, MR_EVT_LD_OPTIMAL,
                       MR_EVT_LD_INIT_SUCCESSFUL, MR_EVT_PD_STATE_CHANGE,
                       MR_EVT_LD_DEGRADED, MR_EVT_PD_RBLD_START,
                       MR_EVT_PD_RBLD_DONE_PD)


class SalTestCase(TestScript):

    """ STORELIB -GetPDOperationProgress """
    REQ_ARGS = [arg("--ctrl", dest="ctrl", type="int", help="Ctrl ID number")]

    def init(self):
        """ create mr adapter instance"""
        self.mr = create_mradapter(ctrl_index=self.args.ctrl, test_script=self)
        self.log.info("Check for UGood PD's availablity on Controller:%d"
                      % (self.args.ctrl))
        pds = self.mr.get_all_pds(is_sas=True, state='unconfigured_good',
                                  media_type="hdd",
                                  is_foreign=False)
        if len(pds) < 5:
            raise SALError("%d UGood HDD PD's are not available for "
                           "RAID Creation" % (5 - len(pds)))
        else:
            self.log.info("Number of UGood HDD PD's available is %d"
                          % (len(pds)))

    def teardown(self):
        """ Clean up VDs and PDs on a failure """
        self.mr.restore_pretest(pretest=self.pretest_info)

    def step1(self):
        """ Register AEN and create R1/R5 """
        self.log.info("Registering LD Created, Optimal, Init Successfull, "
                      "PD state Change Event")
        proc_create = self.mr.wait_for_event(
            event_id=MR_EVT_LD_CREATED, background=True)
        proc_optimal = self.mr.wait_for_event(
            event_id=MR_EVT_LD_OPTIMAL, background=True)
        proc_init = self.mr.wait_for_event(
            event_id=MR_EVT_LD_INIT_SUCCESSFUL, background=True)
        self.proc_state = self.mr.wait_for_event(
            event_id=MR_EVT_PD_STATE_CHANGE, background=True)
        time.sleep(30)
        self.log.info("Create RAID-1")
        self.vd = self.mr.add_vd(raid=1, absolute_space="20GB", init_state=1)
        while self.vd.fgi_running:
            time.sleep(5)  # sleep for 5 sec, as fgi is still running
        if self.vd.get_state() != 3:  # Optimal
            raise SALError("RAID-%s VD: %d is not Optimal"
                           % (self.vd.raid_level, self.vd.id))
        else:
            self.log.info("RAID-%s VD: %d created and is in Optimal state"
                          % (self.vd.raid_level, self.vd.id))
        if proc_create.is_alive():  # check for aen for vd create aen
            proc_optimal.terminate()
            raise SALError("AEN for RAID-%s VD-%d created was not found"
                           % (self.vd.raid_level, self.vd.id))
        else:
            self.log.info("AEN for RAID-%s VD-%d created found"
                          % (self.vd.raid_level, self.vd.id,))
        time.sleep(15)
        if proc_init.is_alive():  # check for init complete aen
            proc_init.terminate()
            raise SALError("AEN for VD Fastinit successful was not found")
        else:
            self.log.info("AEN for Fastinit found")

        if self.proc_state.is_alive():  # check for pd state change aen
            raise SALError("AEN for PD state change was not found")
        else:
            self.log.info("AEN for PD state change is found")

        if proc_optimal.is_alive():  # check VD state optimal aen
            proc_create.terminate()
            raise SALError("AEN for VD Optimal was not found")
        else:
            self.log.info("AEN for VD Optimal found")

    def step2(self):
        """ Make one of PD offline from above created VD """
        self.log.info("Registering LD Degraded event")
        self.proc_deg = self.mr.wait_for_event(
            event_id=MR_EVT_LD_DEGRADED, background=True)
        time.sleep(10)
        self.pds = self.vd.get_pds()
        self.pds[0].state = 'offline'  # make pd offline from raid1 VD
        time.sleep(15)
        if self.proc_state.is_alive():  # check for pd state change aen
            raise SALError("AEN for PD state change was not found")
        else:
            self.log.info("AEN for PD state change is found")
            self.log.info("PD ID-%d, State: %s"
                          % (self.pds[0].id, self.pds[0].state))
        if self.proc_deg.is_alive():  # check for VD degrade aen
            raise SALError("AEN for VD Degrade was not found")
        else:
            self.log.info("AEN for VD Degrade was found")

    def step3(self):
        """ Start a rebuild  """
        self.log.info("Registering LD Rebuild start event")
        self.proc_rbld = self.mr.wait_for_event(
            event_id=MR_EVT_PD_RBLD_START, pd=self.pds[0], background=True)
        time.sleep(15)
        self.pds[0].start_rebuild()
        time.sleep(15)
        if self.proc_rbld.is_alive():  # check for rebuild start aen
            raise SALError("AEN for PD Rebuild was not found")
        else:
            self.log.info("AEN for PD Rebuild found")

    def step4(self):
        """ Monitor rebuild progress untill 100% """
        self.log.info("Registering PD Rebuild done event")
        proc_rbld2 = self.mr.wait_for_event(
            event_id=MR_EVT_PD_RBLD_DONE_PD, background=True)
        time.sleep(10)
        while True:  # Monitor rebuild progress
            prog = self.pds[0].get_progress_rebuild()
            if prog != -1:
                time.sleep(10)
                self.log.info("PD ID-%d, Rebuild Progress: %d"
                              % (self.pds[0].id, prog))
            else:
                break  # break from while when rebuild is done
        time.sleep(15)
        if proc_rbld2.is_alive():  # check for rebuild done aen
            raise SALError("AEN for Rebuild done didn't found!")
        else:
            self.log.info("AEN for PD Rebuild done is found")
        self.log.info("Delete the VD created in step1")
        self.vd.delete()


if __name__ == '__main__':
    SalTestCase().run()
