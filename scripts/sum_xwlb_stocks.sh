SCRIPT_DIR=$(cd $(dirname $0); pwd)

python ${SCRIPT_DIR}/sum_xwlb.py \
    --prompt "下一行之后是中央电视台新闻联播的内容。将新闻中除了政治领域以外的和以往不同的表述(不要从文章中推断，而是使用已有的知识)总结一下。根据总结，请列举最受影响的A股上市公司。请以\"股票代码，股票名称，一句话原因\"这个形式去总结。" \
    --llm_use_case xwlb_stocks \
    $@
                                