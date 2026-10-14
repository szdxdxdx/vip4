#include "CS_Gyro_Att_Predict.h"

void Euler_Estimate(void *p);

void    CS_Gyro_Att_PredictFun(void *p)
{
    CS_Gyro_Att_Predict *pIp = (CS_Gyro_Att_Predict*)p;

	unint32 i;

	/* (1) 惯性角速度计算 */
	for (i = 0; i < 3; i++)
	{
		pIp->csAttCoreData_w_ESG[i] = (pIp->csGyroData_deltag[i] / pIp->m_DeltaT - (pIp->csGyroData_D0_ESCorr[i] + pIp->csGyroData_De_ESCorr[i]) / 3600.0);

		pIp->csAttCoreData_w_ESG[i] = LimitDouble(pIp->csAttCoreData_w_ESG[i], pIp->csGyroPara_Mlfw);
	}

	/* (2) $@调用《三轴欧拉姿态角预估算法产品规范》*/
	/* void Euler_Estimate(float64 *pAngle, float64 *pRate, float64 *wbo,float64 *pwbi, float64 *w0I, unint32 seq, float64 dta)
	输入/出:A_ESG, 输出:Rate_ESG, 输入:wbo_ESG, 输入:w_ESG, 输入:woi,输入:seq, 输入:DeltaT
	*/
	Euler_Estimate(pIp);

	/* (3) */
	/* 角度限幅 */
	for (i = 0; i < 3; i++)
	{
		pIp->csAttCoreData_A_ESG[i] = ModPNHP(pIp->csAttCoreData_A_ESG[i], PI);
	}

	/* ijkHex(16进制整数),必须是1,2,3三个数的组合
	123,表示1-2-3转序
	312,表示3-1-2转序
	依次类推...
	*/
	// CS_Angle2C(pIp->csAttCoreData_Cbo_ESG[0], pIp->csAttCoreData_A_ESG, pIp->csAttPara_Seq_AttD[pIp->m_WorkMode]);
    switch(pIp->csAttPara_Seq_AttD[pIp->m_WorkMode])
    {
    case 123:
        Angle2C123(&pIp->csAttCoreData_Cbo_ESG[0][0], pIp->csAttCoreData_A_ESG[0], pIp->csAttCoreData_A_ESG[1], pIp->csAttCoreData_A_ESG[2]);
        break;
    case 132:
        Angle2C132(&pIp->csAttCoreData_Cbo_ESG[0][0], pIp->csAttCoreData_A_ESG[0], pIp->csAttCoreData_A_ESG[1], pIp->csAttCoreData_A_ESG[2]);
        break;
    case 213:
        Angle2C213(&pIp->csAttCoreData_Cbo_ESG[0][0], pIp->csAttCoreData_A_ESG[0], pIp->csAttCoreData_A_ESG[1], pIp->csAttCoreData_A_ESG[2]);
        break;
    case 231:
        Angle2C231(&pIp->csAttCoreData_Cbo_ESG[0][0], pIp->csAttCoreData_A_ESG[0], pIp->csAttCoreData_A_ESG[1], pIp->csAttCoreData_A_ESG[2]);
        break;
    case 312:
        Angle2C312(&pIp->csAttCoreData_Cbo_ESG[0][0], pIp->csAttCoreData_A_ESG[0], pIp->csAttCoreData_A_ESG[1], pIp->csAttCoreData_A_ESG[2]);
        break;
    case 321:
        Angle2C321(&pIp->csAttCoreData_Cbo_ESG[0][0], pIp->csAttCoreData_A_ESG[0], pIp->csAttCoreData_A_ESG[1], pIp->csAttCoreData_A_ESG[2]);
        break;
    default:
        Angle2C321(&pIp->csAttCoreData_Cbo_ESG[0][0], pIp->csAttCoreData_A_ESG[0], pIp->csAttCoreData_A_ESG[1], pIp->csAttCoreData_A_ESG[2]);
        break;
    }

	/* 角度限幅 */
	for (i = 0; i < 3; i++)
	{
		pIp->csAttCoreData_A_ESG[i] = LimitDouble(pIp->csAttCoreData_A_ESG[i],pIp->csGyroPara_MlfA_ESG[i][pIp->m_WorkMode]);
	}

	return;
}

void Euler_Estimate(void *p)
{
	CS_Gyro_Att_Predict *pIp = (CS_Gyro_Att_Predict*)p;

    float64 cboo[3][3];
    float64 tmat[3];
    siint32 ret;    /* 返回值 */
    float64 tmpatt[3];    /* 增加除０保护 */

    // CS_Angle2C(cboo[0], pIp->pAngle, pIp->seq);  /* Cbo = DCM(ang,seq) */
    switch(pIp->csAttPara_Seq_AttD[pIp->m_WorkMode])
    {
    case 123:
        Angle2C123(&cboo[0][0], pIp->csAttCoreData_A_ESG[0], pIp->csAttCoreData_A_ESG[1], pIp->csAttCoreData_A_ESG[2]);
        break;
    case 132:
        Angle2C132(&cboo[0][0], pIp->csAttCoreData_A_ESG[0], pIp->csAttCoreData_A_ESG[1], pIp->csAttCoreData_A_ESG[2]);
        break;
    case 213:
        Angle2C213(&cboo[0][0], pIp->csAttCoreData_A_ESG[0], pIp->csAttCoreData_A_ESG[1], pIp->csAttCoreData_A_ESG[2]);
        break;
    case 231:
        Angle2C231(&cboo[0][0], pIp->csAttCoreData_A_ESG[0], pIp->csAttCoreData_A_ESG[1], pIp->csAttCoreData_A_ESG[2]);
        break;
    case 312:
        Angle2C312(&cboo[0][0], pIp->csAttCoreData_A_ESG[0], pIp->csAttCoreData_A_ESG[1], pIp->csAttCoreData_A_ESG[2]);
        break;
    case 321:
        Angle2C321(&cboo[0][0], pIp->csAttCoreData_A_ESG[0], pIp->csAttCoreData_A_ESG[1], pIp->csAttCoreData_A_ESG[2]);
        break;
    default:
        Angle2C321(&cboo[0][0], pIp->csAttCoreData_A_ESG[0], pIp->csAttCoreData_A_ESG[1], pIp->csAttCoreData_A_ESG[2]);
        break;
    }
    MatrixMulti(tmat, cboo[0], &pIp->csOrbData_w0i[0], 3, 3, 1);

    pIp->csAttCoreData_wbo_ESG[0] = pIp->csAttCoreData_w_ESG[0] - tmat[0];
    pIp->csAttCoreData_wbo_ESG[1] = pIp->csAttCoreData_w_ESG[1] - tmat[1];
    pIp->csAttCoreData_wbo_ESG[2] = pIp->csAttCoreData_w_ESG[2] - tmat[2];

    /* w2dAngle(pRate, pIp->pAngle, wbo, (siint32)seq); 转序seq改成十进制了，改调下面这个 */
    // CS_w2dAngleDec(pIp->pRate, pIp->pAngle, pIp->wbo, (siint32)pIp->seq);

    tmpatt[0] = pIp->csAttCoreData_A_ESG[0];
    tmpatt[1] = pIp->csAttCoreData_A_ESG[1];
    tmpatt[2] = pIp->csAttCoreData_A_ESG[2];

    switch ((siint32)pIp->csAttPara_Seq_AttD[pIp->m_WorkMode])
    {
    case 123:
        if(Fabsx(Cosx(tmpatt[1])) < 1.0e-7)
        {
            tmpatt[1] = tmpatt[1] + 0.001;
        }
        w2dAngle123(pIp->csAttCoreData_Rate_ESG, tmpatt, pIp->csAttCoreData_wbo_ESG);  /* 调用原有函数计算 */
        ret = 0;                          /* 转序有效，计算成功 */
        break;

    case 132:
        if(Fabsx(Cosx(tmpatt[2])) < 1.0e-7)
        {
            tmpatt[2] = tmpatt[2] + 0.001;
        }
        w2dAngle132(pIp->csAttCoreData_Rate_ESG, tmpatt, pIp->csAttCoreData_wbo_ESG);  /* 调用原有函数计算 */
        ret = 0;                          /* 转序有效，计算成功 */
        break;

    case 213:
        if(Fabsx(Cosx(tmpatt[0])) < 1.0e-7)
        {
            tmpatt[0] = tmpatt[0] + 0.001;
        }
        w2dAngle213(pIp->csAttCoreData_Rate_ESG, tmpatt, pIp->csAttCoreData_wbo_ESG);  /* 调用原有函数计算 */
        ret = 0;                          /* 转序有效，计算成功 */
        break;

    case 231:
        if(Fabsx(Cosx(tmpatt[2])) < 1.0e-7)
        {
            tmpatt[2] = tmpatt[2] + 0.001;
        }
        w2dAngle231(pIp->csAttCoreData_Rate_ESG, tmpatt, pIp->csAttCoreData_wbo_ESG);  /* 调用原有函数计算 */
        ret = 0;                          /* 转序有效，计算成功 */
        break;

    case 321:
        if(Fabsx(Cosx(tmpatt[1])) < 1.0e-7)
        {
            tmpatt[1] = tmpatt[1] + 0.001;
        }
        w2dAngle321(pIp->csAttCoreData_Rate_ESG, tmpatt, pIp->csAttCoreData_wbo_ESG);  /* 调用原有函数计算 */
        ret = 0;                          /* 转序有效，计算成功 */
        break;

    case 312:
        if(Fabsx(Cosx(tmpatt[0])) < 1.0e-7)
        {
            tmpatt[0] = tmpatt[0] + 0.001;
        }
        w2dAngle312(pIp->csAttCoreData_Rate_ESG, tmpatt, pIp->csAttCoreData_wbo_ESG);  /* 调用原有函数计算 */
        ret = 0;                          /* 转序有效，计算成功 */
        break;

    default:

        /* 角速率清零 */
        pIp->csAttCoreData_Rate_ESG[0] = 0.0;
        pIp->csAttCoreData_Rate_ESG[1] = 0.0;
        pIp->csAttCoreData_Rate_ESG[2] = 0.0;

        ret = -1;                         /* 转序无效，计算失败 */
        break;
    }

    pIp->csAttCoreData_A_ESG[0] = pIp->csAttCoreData_A_ESG[0]+pIp->csAttCoreData_Rate_ESG[0]*pIp->m_DeltaT;
    pIp->csAttCoreData_A_ESG[1] = pIp->csAttCoreData_A_ESG[1]+pIp->csAttCoreData_Rate_ESG[1]*pIp->m_DeltaT;
    pIp->csAttCoreData_A_ESG[2] = pIp->csAttCoreData_A_ESG[2]+pIp->csAttCoreData_Rate_ESG[2]*pIp->m_DeltaT;

    return;
}