#include "NWM.h"
#include "CS_PrecessionNutationCal.h"

void CPNCalc(void *p, float64 tJ2000);

void CS_PrecessionNutationCalFun(void *p)
{
    CS_PrecessionNutationCal *pIp = (CS_PrecessionNutationCal*)p;

    float64 tJ2000;

    F_qJDerr = 0;

    if (FS_CPNCal == 1)
    {
        tJ2000 = pIp->tmpT + UTC0 + tGPS0 + dT_UTC2TDT;

        /* 调用《岁差章动矩阵计算算法产品规范》计算岁差章动矩阵Cpn */
        CPNCalc(pIp, tJ2000);

    }
    else
    {
        if (TripleFabsMax(qJD[0], qJD[1], qJD[2]) < 0.05)
        {
            qJD[3] = Sqrtx(1.0 - qJD[0]*qJD[0] -
                                            qJD[1]*qJD[1] -
                                            qJD[2]*qJD[2]);

            Q2C(&CPN[0][0], &qJD[0]);      /* 由qJD计算CPN */
        }
        else
        {
            /* 置单位阵 */
            MatrixIdentity33(&CPN[0][0]);

            F_qJDerr = 1;
        }
    }

    return;
}



void CPNCalc(void *p, float64 tJ2000)
{
    CS_PrecessionNutationCal *pIp = (CS_PrecessionNutationCal*)p;

    float64 Tc;
    float64 zeta_p;
    float64 Zp;
    float64 theta_p;
    float64 Cp[3][3];                       /* 岁差矩阵 */
    float64 Cn[3][3];                       /* 章动矩阵 */
    float64 TransCp[3][3], TransCn[3][3];   /* 岁差矩阵、章动矩阵的转置 */
    float64 tmp1[3][3], tmp2[3][3], tmp3[3][3], tmp4[3][3];
    float64 OMG, F, D, M;
    float64 delta_psi;
    float64 delta_eps, eps, eps_mean;

    Tc = tJ2000 / (86400.0 * 36525.0);
    zeta_p = CPN_POLY3(0.0, 2306.2181, 0.30188, 0.017998, Tc);
    Zp = CPN_POLY3(0.0, 2306.2181, 1.09468, 0.018203, Tc);
    theta_p = CPN_POLY3(0.0, 2004.3109, -0.42665, -0.041833, Tc);

    Rz(tmp1[0], -Zp);
    Ry(tmp2[0],  theta_p);
    Rz(tmp3[0], -zeta_p);
    MatrixMulti333(&tmp4[0][0], &tmp1[0][0], &tmp2[0][0]);
    MatrixMulti333(&Cp[0][0],   &tmp4[0][0], &tmp3[0][0]);      /* 得到岁差矩阵Cp[3][3] */

    OMG = CPN_POLY3(450160.280, -6962890.539, 7.455, 0.008, Tc);
    F = CPN_POLY3(335778.877,  1739527263.137, -13.257, 0.011, Tc);
    D = CPN_POLY3(1072261.307, 1602961601.328, -6.891, 0.019, Tc);
    M = CPN_POLY3(1287099.804, 129596581.224, -0.577, -0.012, Tc);

    delta_psi = -CPN_POLY1(17.1996, 0.01742, Tc) * Sinx(OMG) + CPN_POLY1(0.2026, 0.00002, Tc) * Sinx(2.0*OMG) -
                    CPN_POLY1(1.3187,  0.00016, Tc) * Sinx(2.0 * (F - D + OMG)) + CPN_POLY1(0.1426, -0.00034, Tc) * Sinx(M) -
                    CPN_POLY1(0.2274,  0.00002, Tc) * Sinx(2.0 * (F + OMG));
    delta_eps = CPN_POLY1(9.2025,  0.00089, Tc) * Cosx(OMG) - CPN_POLY1(0.0895, -0.00005, Tc) * Cosx(2.0*OMG) +
                CPN_POLY1(0.5736, -0.00031, Tc) * Cosx(2.0 * (F - D + OMG)) + CPN_POLY1(0.0977, -0.00005, Tc) * Cosx(2.0 * (F + OMG)) +
                CPN_POLY1(0.0054, -0.00001, Tc) * Cosx(M);
    eps       = CPN_POLY3(84381.448, -46.8150, -0.00059, 0.001813, Tc);

    /* 考虑岁差影响的黄赤交角ε */
    eps_mean = eps - delta_eps;        /* 平黄赤交角 */

    Rx(tmp1[0], -(eps_mean + delta_eps));
    Rz(tmp2[0], -delta_psi);
    Rx(tmp3[0], eps_mean);
    MatrixMulti333(&tmp4[0][0], &tmp1[0][0], &tmp2[0][0]);
    MatrixMulti333(  &Cn[0][0], &tmp4[0][0], &tmp3[0][0]);      /* 得到章动矩阵Cn[3][3] */

    MatrixTran33(&TransCp[0][0], &Cp[0][0]);
    MatrixTran33(&TransCn[0][0], &Cn[0][0]);
    MatrixMulti333(&CPN[0][0], &TransCp[0][0], &TransCn[0][0]);    /* 岁差章动矩阵CPN*/

    return;
}