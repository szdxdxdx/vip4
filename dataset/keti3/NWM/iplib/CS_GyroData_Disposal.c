#include "CS_GyroData_Disposal.h"

void CS_GyroData_DisposalFun(void *p)
{
    CS_GyroData_Disposal *pIp = (CS_GyroData_Disposal*)p;

    unint32 i;
    unint32 j;
    unint32 k;
    unint32 n;
    float64 MatrixR3[3][3];
    float64 MatrixR4[4][3];
    float64 TunMatR4[3][4];
    float64 Matr4[3][4];
    float64 Matr[3][3];
    float64 InvMatr[3][3];
    float64 dg3[3];
    float64 dg4[4];

    /* 陀螺定姿下无陀螺组合时停控 */
    if (( pIp->csGyroDiagData_F_NoUseGroup == 1) &&
        ((pIp->csAttPara_FS_AttD == 0) || (pIp->csAttPara_FS_AttD == 1)) &&
        ( pIp->csGyroDiagPara_FP_ModeStopCtrl[pIp->m_WorkMode] == 1))
    {
        pIp->csModeData_F_StopCtrl = 1;
    }
    else
    {
        pIp->csModeData_F_StopCtrl = 0;
    }

    /* 有效陀螺个数 */
    for (i = 0,n = 0; i < 9; i++)
    {
        if (pIp->csGyroDiagData_FU_ing[i] == 1)
        {
            n++;
        }
    }

    /* (1) 停控或可用陀螺数不足 使用历史值 */
    if (( pIp->csModeData_F_StopCtrl == 1) ||
        ((n != 3) && (n != 4)))
    {
        for (i = 0; i < 3; i++)
        {
            pIp->csGyroData_deltag[i] = pIp->csGyroData_deltag_Lst[i];
        }
    }
    else
    {
        /* (2) 四陀螺  */
        if (n == 4)
        {
            for (i = 0,k = 0; ( (i < 9) && (k < 4)); i++)
            {
                if (pIp->csGyroDiagData_FU_ing[i] == 1)
                { /* 该陀螺有效 */
                    for (j = 0; j < 3; j++)
                    {
                        MatrixR4[k][j] = pIp->csGyroPara_Vbs[i][j];
                    }
                    dg4[k] = pIp->csGyroData_deltagm[i];
                    k++;
                }
            }
            MatrixTran(TunMatR4[0], MatrixR4[0],  4, 3);
            MatrixMulti(Matr[0], TunMatR4[0], MatrixR4[0], 3, 4, 3);
            MatrixInv33(InvMatr[0], Matr[0]);
            MatrixMulti(Matr4[0], InvMatr[0], TunMatR4[0], 3, 3, 4);
            MatrixMulti(pIp->csGyroData_deltag, Matr4[0], dg4, 3, 4, 1);
        }
        else
        {
                        /* (3) 三陀螺  */
            if (n == 3)
            {
                for (i = 0,k = 0; ((i < 9)&&(k < 3)); i++)
                {
                    if (pIp->csGyroDiagData_FU_ing[i] == 1)
                    { /* 该陀螺有效 */
                        for (j = 0; j < 3; j++)
                        {
                            MatrixR3[k][j] = pIp->csGyroPara_Vbs[i][j];
                        }
                        dg3[k] = pIp->csGyroData_deltagm[i];
                        k++;
                    }
                }

                MatrixInv33(InvMatr[0], MatrixR3[0]);
                MatrixMulti(pIp->csGyroData_deltag, InvMatr[0], dg3,  3, 3, 1);
            }
        }

        /* (4) */
        for (i = 0; i < 3; i++)
        {
            pIp->csGyroData_wbi[i] = pIp->csGyroData_deltag[i] / m_DeltaT;
            pIp->csGyroData_wbi[i] = LimitDouble(pIp->csGyroData_wbi[i], pIp->csGyroPara_Mlfw);
            pIp->csGyroData_deltag_Lst[i] = pIp->csGyroData_deltag[i];		/* 保存历史值 */
        }
    }

    return;
}
