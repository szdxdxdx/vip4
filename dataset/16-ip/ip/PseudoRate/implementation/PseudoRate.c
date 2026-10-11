#include "PseudoRate.h"

void PseudoRateFun(void *p) {
    PseudoRate *pIp = (PseudoRate *)p;
    unint32 i;
    for (i = 0; i < 3; i++) {
        if ((pIp->pu[i] - pIp->r[i]) > pIp->h1[i]) {/* u(输入)-r（反馈信号）>h1 */
            pIp->Yp[i] = 0x0; /* 产生32ms正脉冲 */
            pIp->Yn[i] = 0xF;
            pIp->r[i] = 0.9231f * pIp->r[i] + 0.07688f; /*  Y=1 */
        } else if ((pIp->pu[i] - pIp->r[i]) < -pIp->h1[i]) { /* u(输入)-r（反馈信号）<h1 */
            pIp->Yp[i] = 0xF; /* 产生32ms负脉冲 */
            pIp->Yn[i] = 0x0;
            pIp->r[i] = 0.9231f * pIp->r[i] - 0.07688f; /* Y=-1  */
        } else { /* 其他 */
            pIp->Yp[i] = 0x0; /* 不喷 */
            pIp->Yn[i] = 0x0;
            pIp->r[i] = 0.9231f * pIp->r[i]; /* Y=0  */
        }
    }
    return;
}
