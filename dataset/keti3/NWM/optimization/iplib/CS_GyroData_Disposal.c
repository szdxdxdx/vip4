#include "NWM.h"
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
    if (( F_NoUseGroup == 1) &&
        ((FS_AttD == 0) || (FS_AttD == 1)) &&
        ( FP_ModeStopCtrl[WorkMode] == 1))
    {
        F_StopCtrl = 1;
    }
    else
    {
        F_StopCtrl = 0;
    }

    /* 有效陀螺个数 */
    for (i = 0,n = 0; i < 9; i++)
    {
        if (FUsing_gyro[i] == 1)
        {
            n++;
        }
    }

    /* (1) 停控或可用陀螺数不足 使用历史值 */
    if (( F_StopCtrl == 1) ||
        ((n != 3) && (n != 4)))
    {
        for (i = 0; i < 3; i++)
        {
            deltG[i] = pIp->csGyroData_deltag_Lst[i];
        }
    }
    else
    {
        /* (2) 四陀螺  */
        if (n == 4)
        {
            for (i = 0,k = 0; ( (i < 9) && (k < 4)); i++)
            {
                if (FUsing_gyro[i] == 1)
                { /* 该陀螺有效 */
                    for (j = 0; j < 3; j++)
                    {
                        MatrixR4[k][j] = Vbs[i][j];
                    }
                    dg4[k] = deltGm[i];
                    k++;
                }
            }
            MatrixTran(TunMatR4[0], MatrixR4[0],  4, 3);
            MatrixMulti(Matr[0], TunMatR4[0], MatrixR4[0], 3, 4, 3);
            MatrixInv33(InvMatr[0], Matr[0]);
            MatrixMulti(Matr4[0], InvMatr[0], TunMatR4[0], 3, 3, 4);
            MatrixMulti(deltG, Matr4[0], dg4, 3, 4, 1);
        }
        else
        {
                        /* (3) 三陀螺  */
            if (n == 3)
            {
                for (i = 0,k = 0; ((i < 9)&&(k < 3)); i++)
                {
                    if (FUsing_gyro[i] == 1)
                    { /* 该陀螺有效 */
                        for (j = 0; j < 3; j++)
                        {
                            MatrixR3[k][j] = Vbs[i][j];
                        }
                        dg3[k] = deltGm[i];
                        k++;
                    }
                }

                MatrixInv33(InvMatr[0], MatrixR3[0]);
                MatrixMulti(deltG, InvMatr[0], dg3,  3, 3, 1);
            }
        }

        /* (4) */
        for (i = 0; i < 3; i++)
        {
            wbi[i] = deltG[i] / m_DeltaT;
            wbi[i] = LimitDouble(wbi[i], Mlfw);
            pIp->csGyroData_deltag_Lst[i] = deltG[i];		/* 保存历史值 */
        }
    }

    return;
}
