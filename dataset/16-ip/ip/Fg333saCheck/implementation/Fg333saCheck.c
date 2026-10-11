#include "Fg333saCheck.h"

static unint08 CheckSumAdd08(const unint08 *buf, unint32 num) {
    unint32 sum = 0;
    for (unint32 i = 0; i < num; i++) {
        sum = sum + buf[i];
    }
    return (unint08)(sum % 255);
}

/*
fg_3_3_3sa协议校验IP

功能描述：
  校验接收到的数据是否符合 Fg333 型光纤陀螺通信协议，校验成功返回 TRUE32，否则返回 FALSE32。
  1.校验数据长度是否正确：若长度不为 19，则 cntLenRd、totalLenRd+1，返回校验失败；
  2.校验帧计数是否更新：若帧计数不更新，则 cntUpdata、totalUpdata+1，返回校验失败；
  3.校验帧头是否正确：若帧头非 0xEB90，则 cntHead、totalHead+1，返回校验失败；
  4.校验累加和是否正确：若累加和正确则返回校验成功，否则返回校验失败。
*/
void Fg333saCheckFun(void *pIp) {
    unint08 chksum;
    Fg333saCheck *p = (Fg333saCheck *)pIp;

    p->bComSuc = FALSE32;

    if (p->rdLen == 19) {
        p->cntLenRdS = 0;

        /* 帧计数是否更新 */
        if (p->pbuff[17] != (p->frm)) {
            p->cntUpdataS = 0;
            p->cntUpdataO = 0;
            p->frm = p->pbuff[17];

            /* 帧头为0xEB90 */
            if ((p->pbuff[0] == 0xEB) && (p->pbuff[1] == 0x90)) {
                p->cntHeadS = 0;
                p->cntHeadO = 0;
                /* 计算累加和 */
                chksum = CheckSumAdd08(&p->pbuff[0], 18);

                /* 累加和正确 */
                if (chksum == p->pbuff[18]) {
                    p->cntCheckS = 0;
                    p->cntCheckO = 0;
                    p->bComSuc = TRUE32;
                } else {
                    /* 累加和不正确 */
                    p->cntCheckS++;
                    p->totalCheckS++;
                    p->cntCheckO++;
                    p->totalCheckO++;
                }
            } else {
                /* 帧头不正确 */
                p->cntHeadS++;
                p->totalHeadS++;
                p->cntHeadO++;
                p->totalHeadO++;
            }
        } else {
            /* 帧计数不更新 */
            p->cntUpdataS++;
            p->totalUpdataS++;
            p->cntUpdataO++;
            p->totalUpdataO++;
        }
    } else {
        /* 数据长度不对 */
        p->cntLenRdS++;
        p->totalLenRdS++;
        p->cntLenRdO++;
        p->totalLenRdO++;
    }
    return;
}
