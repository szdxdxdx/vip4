#include "code.h"

/* 内置字节累加和组件，算法与 348 的 CheckCalFun 一致。 */
typedef struct __CheckCal
{
    Fun fun;
    unint08 *pkv;
    unsigned int len;
    unint08 chksum;
} CheckCal;

static void CheckCalFun(void *p)
{
    CheckCal *pIp = (CheckCal*)p;
    unsigned int i;

    pIp->chksum = 0;
    for (i = 0; i < pIp->len; i++)
    {
        pIp->chksum = (unint08)(pIp->chksum + pIp->pkv[i]);
    }
}

void B_TcProcessFun(void *p)
{
    B_TcProcess *pIp = (B_TcProcess*)p;

	CheckCal ip1 = { .fun = CheckCalFun, .pkv = &pIp->tcaData[0], .len = 3, .chksum = 0 };

	if ((pIp->tcaData[0] == 0xE1) && (pIp->tcaData[1] == 0x00))					/* 包头正确 */
	{		
        ip1.fun(&ip1);

	    if(pIp->tcaData[3] == ip1.chksum)
	    {
	    	/* 校验和正确 */
	    	if(pIp->tcaData[2] == 0)
	    	{
                *pIp->workMode = SAM_DAMP;
	    	}
	    	else if(pIp->tcaData[2] == 1)
	    	{
                *pIp->workMode = SAM_CRUISE;
	    	}
	    	else
	    	{
                *pIp->workMode = NOCTRL;
	    	}
	    }
	}
    return;
}
