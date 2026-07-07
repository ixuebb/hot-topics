# Video Moment Retrieval / Temporal Grounding Idea 报告：10 个候选题目、摘要与引言

生成日期：2026-06-27  
数据来源：`D:\syz_autopaper\auto_idea\video moment retrieval\idea_graph` 中的细粒度 idea 图谱。  
依据文件：`idea_opportunities_finegrained.json`、`micro_problem_clusters.json`、`micro_method_clusters.json`、`paper_micro_cards_index.json`。  

说明：本报告不是实验结果报告，而是基于本地 300 篇已解析论文卡片、145 个核心微问题、229 个微方法和 60 个细粒度迁移机会生成的研究 idea 草案。这里的题目、摘要和引言可以作为后续 AAAI/CVPR/NeurIPS 风格论文立项的第一版写作素材；所有性能提升均应在后续实验中验证，不能直接写成已证明结论。

## 选择原则

1. 不机械选择分数最高的前 10 个，因为前几名存在同一个问题族和同一种方法的重复组合。
2. 优先选择问题机制不同、可迁移方法明确、验证数据集明确的方向。
3. 每个题目都保留与当前图谱的对应关系，便于回到前端 root exploration view 中继续追论文证据。
4. 引言采用“任务背景 -> 现有痛点 -> 为什么现有方法没解决 -> 本文主张”的结构，便于后续扩展为正式论文 Introduction。

## 10 个候选题目概览

| 编号 | 题目 | 对应图谱 idea | 核心问题 | 迁移机制 |
| --- | --- | --- | --- | --- |
| 1 | 面向长视频稀疏证据发现的结构化证据链世界模型 | FI001 | 长视频中低频关键证据被冗余 token 淹没 | SMORE / Diffusion / structured reasoning |
| 2 | 面向硬无关查询的视频时序定位证据校准拒识 | FI006 | open-set hard-irrelevant query 难拒绝 | evidential learning / query reconstruction |
| 3 | 上下文扰动下的边界语义稳定性与不确定性感知定位 | FI005 | temporal boundary 表征随上下文替换漂移 | evidential calibration / Geom regularization |
| 4 | 面向动态视频-文本交互的动作线索注入式反应-扩散提示模型 | FI008 | 固定融合模式难适配动态时空交互 | action cue prompt / reaction-diffusion fusion |
| 5 | 面向通用长视频时间定位的上下文扭曲预训练与显式时间推理 | FI012 | MLLM 长上下文窗口和显存限制 | context warping / multi-scale reasoning |
| 6 | 面向跨域视频时序定位的实体证据路由与去偏校准 | FI011 | source-domain shortcut 和实体注意力继承不足 | entity-grounded routing / de-bias calibration |
| 7 | 面向多干扰视频检索的证据充分性与忠实性评估 | FI016 | VMR 在 distractor video 上过度自信 | evidence sufficiency / abstention |
| 8 | 面向弱监督定位的语义负样本重构差异挖掘 | FI026 | within-video hard negative 被忽略 | reconstruction-discrepancy mining |
| 9 | 面向弱监督长视频定位的因果高斯边界优化 | FI037 | proposal-to-boundary 映射无法保证最优边界 | Gaussian boundary optimization / causal prior |
| 10 | 面向上下文增强训练的查询相关内容替换与假负样本修复 | FI048 | query-agnostic context mixing 造成 false negative | reconstruction discrepancy / query-aware replacement |

---

## Idea 1：面向长视频稀疏证据发现的结构化证据链世界模型

对应图谱：FI001，score 10.49，目标问题 MP0139，方法来源 MM0006。  
证据论文包括：Unleashing the Potential of Multimodal LLMs for Zero-Shot Spatio-Temporal Video Grounding、See More, Store Less、Mamba-based Modulated Fusion Model for VMR、SafePLUG。

### 摘要

长视频时序定位的核心困难正在从“短视频边界回归”转向“长上下文中的稀疏证据发现”。现有 MLLM 或 Transformer 式方法虽然具备强大的跨模态语义对齐能力，但在处理长视频时容易被冗余视觉 token、系统 token、特殊 token 和高显著片段干扰，导致真正决定答案的低频关键证据被淹没。本文提出一种结构化证据链世界模型，将视频理解过程建模为显式证据状态的演化：模型先压缩冗余帧 token，再围绕查询维护候选事件、局部证据、时间关系和边界置信度，并通过迭代式证据链更新完成 moment localization。该思路吸收 SMORE 的信息分辨率控制、Mamba/agentic reasoning 的长程时序组织能力，以及 diffusion-style refinement 的逐步修正机制。实验可在 QVHighlights、Charades-STA、ActivityNet Captions 和 Ego4D-NLQ 上验证，重点报告长视频、低频证据、跨片段证据链和显存效率场景下的定位性能。

### 引言

Video Moment Retrieval 和 Video Temporal Grounding 的目标是根据自然语言查询，在未裁剪视频中定位对应的时间片段。早期方法主要围绕局部片段打分、proposal ranking 或边界回归展开，在短视频和单事件查询上已经取得较好表现。然而，近期数据集和应用场景正在快速转向长视频、开放查询、多事件组合和 MLLM 辅助推理。此时，模型面对的不再是一个短片段内的语义匹配问题，而是在大量冗余帧和复杂上下文中寻找少量真正决定答案的证据。

当前图谱中，长视频稀疏证据是最强的高新问题之一。相关论文指出，MLLM 视觉 grounding 工作常关注生成 token 或最终答案，却忽略输入中的系统 token、特殊 token 以及不同 token 对定位决策的影响；另一些工作则指出，密集帧处理会带来显存压力和信息冗余，稀疏采样又可能错过关键场景。SMORE 的思想是“see more, store less”，通过查询感知的重要性调制和信息分辨率控制减少冗余信息；Mamba-based fusion 和 SafePLUG 则从长程时序建模或像素级理解角度强调 temporal reasoning 的必要性。

这些工作说明了一个共同趋势：未来 VMR 不能只依靠更大的视觉编码器或更强的 cross-attention，而需要显式维护“证据如何被发现、保留、组合和验证”的过程。若关键证据只在长视频中短暂出现，普通注意力模型可能会被高频背景、显著动作或语言先验吸引；若模型没有显式记忆机制，它也难以把早期线索、后续状态和最终边界连接起来。

本文主张构建结构化证据链世界模型。所谓世界模型，不是要预测完整视频未来，而是为 temporal grounding 维护一个可更新的证据状态空间：每个状态包含候选事件、支持帧、反证帧、时间先后关系、边界分布和不确定性。模型通过 token compression 过滤冗余视觉输入，通过 structured reasoning 生成证据链，通过 iterative refinement 修正边界。相比单次边界回归，该框架可以给出更可解释的证据路径，并允许设计低频证据召回率、证据链完整度和边界置信度等诊断指标。

---

## Idea 2：面向硬无关查询的视频时序定位证据校准拒识

对应图谱：FI006，score 10.22，目标问题 MP0004，方法来源 MM0057。  
证据论文包括：Learning to Refuse、Adaptive Evidential Learning for Temporal-Semantic Robustness in Moment Retrieval、URPA、Embracing Uncertainty。

### 摘要

开放集视频时序定位要求模型不仅能定位相关查询，还能在查询与视频不匹配时拒绝回答。现有拒识方法通常能处理完全无关的随机查询，但在 hard-irrelevant queries 上仍容易失败：这些查询与视频语义接近，却没有真实对应片段。本文提出证据校准拒识框架，将 query reconstruction、跨模态证据一致性和 evidential uncertainty 结合起来，把“是否存在足够证据支持该查询”作为拒识判据，而不是只依靠最高匹配分数。模型在预测边界的同时估计证据充分性、语义覆盖率和不确定性，并使用几何正则抑制高置信错误定位。该方向可在 Learning to Refuse 所提出的 hard-irrelevant setting、MAD、ActivityNet Captions 和 Charades-STA 上验证，重点评估 refusal accuracy、accepted-query localization accuracy 和 calibration error。

### 引言

传统 VMR 默认每个查询在视频中都有对应片段。因此，即使查询与视频不匹配，模型也往往会被迫输出一个最高分片段。这一假设在封闭数据集上方便训练和评估，但在真实应用中并不成立。用户可能提出错误描述、近似描述、外部事件描述，或与视频背景相似但并不存在的 hard-irrelevant query。若模型仍给出高置信答案，系统就会产生严重误导。

当前图谱中，hard-irrelevant query 被识别为一个新近且可发的问题。Learning to Refuse 指出现有方法虽然能拒绝完全无关的查询，却无法可靠拒绝与视频语义接近但实际没有对应片段的查询。这说明拒识问题不能只靠视频-文本总体相似度解决，因为 hard-irrelevant query 往往共享对象、场景或动作词，只是在时序组合、事件关系或局部证据上不成立。

另一方面，Adaptive Evidential Learning 和 Embracing Uncertainty 表明，不确定性估计可以为 temporal grounding 提供比普通分数更细的诊断信号。尤其是 query reconstruction、dual-branch fusion 和 Geom regularizer 能够缓解跨模态融合中的过度自信。URPA 进一步说明，在无标签跨域场景中，不确定性可以指导策略适配。把这些机制迁移到 open-set temporal grounding 中，可以从“最高分是否足够高”转向“证据是否足够支持该查询”。

本文主张建立证据校准拒识模型。模型首先学习 query-conditioned evidence map，随后重构查询语义并估计视频片段能解释查询的程度。如果模型只能通过背景或局部词匹配获得高分，而无法重构关键事件关系，则应提升不确定性并触发拒识。该框架可以把定位、拒识和校准统一在一个训练目标中，并引入 hard-negative curriculum，使模型逐渐区分 completely irrelevant、semantically close but absent 和 truly grounded 三类查询。

---

## Idea 3：上下文扰动下的边界语义稳定性与不确定性感知定位

对应图谱：FI005，score 10.26，目标问题 MP0105，方法来源 MM0057。  
证据论文包括：CVA: Context-aware Video-text Alignment for Video Temporal Grounding、MASRA、Adaptive Evidential Learning、URPA。

### 摘要

Temporal grounding 的边界预测高度依赖局部片段及其周围上下文。当训练或增强过程中替换 surrounding context 时，真实边界片段可能被错误地视为 hard negative，或者其表征随背景变化而漂移，导致模型学习到不稳定的边界语义。本文提出上下文扰动下的边界语义稳定性框架，将 context-invariant boundary discrimination 与 evidential calibration 结合：模型不仅约束边界片段在不同上下文中的语义一致性，还估计边界证据是否充分、是否受到上下文污染。方法可通过 query-aware context replacement 构造扰动样本，通过 Geom-regularized evidential loss 抑制边界附近的过度自信。实验可基于 CVA 在 Charades-STA、QVHighlights 和 ActivityNet Captions 上开展，并报告边界 IoU、near-boundary error、context-shift robustness 和 uncertainty calibration。

### 引言

视频时序定位看似是一个边界回归问题，但边界本身并不是孤立存在的。一个动作的开始和结束常常需要借助前后上下文判断，例如准备动作、状态变化、交互对象出现或消失等。因此，模型如果只学习局部片段相似度，就容易在上下文发生变化时产生边界漂移。

CVA 明确提出 context-aware video-text alignment 的重要性，并引入 context-invariant boundary discrimination loss，使困难边界在多样上下文下保持语义一致。这个观察非常关键：当上下文增强采用 query-agnostic replacement 时，替换片段可能仍与查询相关，从而形成 false negative；当边界周围片段被替换时，模型也可能把原本正确的边界推向错误表征空间。MASRA 进一步指出，当前训练范式缺少 dense semantic supervision 和 local relational supervision。

与此同时，evidential learning 提供了另一种处理边界歧义的工具。边界附近本来就比事件中心更不确定，模型不应对所有片段给出同等置信度。Adaptive Evidential Learning 中的 Geom regularizer 说明，可以根据预测准确性调节不确定性，抑制高错误低不确定性的反直觉现象。把这种机制引入边界扰动场景，可以让模型识别“上下文不足以稳定支持该边界”的样本。

本文主张将边界语义稳定性和不确定性校准统一建模。具体而言，模型在原视频和扰动视频中同时预测边界表征，要求真实边界在语义空间保持一致，同时对边界附近 hard negative 分配更高不确定性。这样既能提升标准 R@1 和 mIoU，也能在上下文替换、视频裁剪、背景干扰等场景下提升鲁棒性。

---

## Idea 4：面向动态视频-文本交互的动作线索注入式反应-扩散提示模型

对应图谱：FI008，score 10.02，目标问题 MP0127，方法来源 MM0023。  
证据论文包括：Turing Patterns for Multimedia: Reaction-Diffusion Multi-Modal Fusion、ActPrompt、Saliency-Guided DETR、Video-Text Prompting。

### 摘要

视频-文本定位中的跨模态融合常采用固定 attention 或静态 token interaction，难以适应动作、对象和文本约束随时间共同变化的动态过程。Reaction-Diffusion Multi-Modal Fusion 将视频帧和文本查询视为相互作用的动态系统，为跨模态融合提供了新的建模角度；ActPrompt 则证明 action cues 可以引导 VLM 捕捉动作敏感模式。本文提出动作线索注入式反应-扩散提示模型：先从视频和语言中提取 action-sensitive cues，再把它们注入到反应-扩散式跨模态场中，使相关动作区域在时间上扩散、竞争和稳定成可定位的 moment。该方法可以缓解静态对象偏置和固定融合模式不足。实验可在 QVHighlights、Charades-STA 和 ActivityNet Captions 上验证，并重点分析 action-heavy queries、static-object distractors 和动态场可视化。

### 引言

视频时序定位不仅需要识别对象和场景，更需要理解动作如何随时间发生。很多查询的关键语义来自动词、动作状态变化或对象交互，而不是静态视觉外观。例如“person opens the door”和“person stands near the door”可能共享对象和场景，却对应完全不同的时间片段。若模型主要依赖静态视觉 token 或固定 cross-attention，就容易产生动作不敏感的匹配。

RDMF 将跨模态融合类比为 reaction-diffusion system，强调视频帧和文本查询之间存在动态、非线性的相互作用。这种思想适合 temporal grounding，因为查询语义不应一次性静态注入所有帧，而应在时间轴上与候选片段反复交互、扩散和抑制。与此同时，ActPrompt 提出从视频和文本编码器生成 action cues，并作为 prompt embeddings 注入 VLM 图像编码器，从而捕捉 action-sensitive patterns。

这两类方法之间存在明显迁移空间。RDMF 提供动态融合场，但可能缺少明确的动作语义锚点；ActPrompt 提供动作线索，但主要作为 prompt adaptation 使用，尚未充分建模 temporal field 中的扩散和竞争。若将 action cues 作为反应-扩散场的外部激励，就可以让动作相关区域在时间上逐步增强，让静态背景或对象共现片段被抑制。

本文主张构建 action-cue-injected reaction-diffusion prompting。模型首先抽取 verb-guided 和 video-guided action prompts，然后把它们注入多层跨模态融合场，使视频 token 的激活随查询动作约束动态演化。最终边界由稳定后的 action field 和文本一致性共同决定。该方向的亮点在于既有直观可视化，又能设计面向 action-heavy queries 的诊断实验。

---

## Idea 5：面向通用长视频时间定位的上下文扭曲预训练与显式时间推理

对应图谱：FI012，score 9.67，目标问题 MP0070，方法来源 MM0205。  
证据论文包括：Universal Video Temporal Grounding with Generative MLLMs、Seq2Time、TimeRefine、LocVTP、RDMF。

### 摘要

通用视频时间定位希望使用 generative MLLM 处理跨数据集、跨任务、跨视频长度的 temporal grounding，但长视频输入往往包含数万 token，受限于上下文窗口和显存，模型难以进行稳定的显式时间推理。本文提出上下文扭曲预训练与显式时间推理框架，把 temporal relation reasoning 转化为可学习的 context warping pretext task：模型在预训练阶段学习不同片段之间的先后、持续、重叠和因果关系，在推理阶段通过多尺度上下文摘要和显式时间链生成定位结果。该方向结合 LocVTP 的 context warping、Universal VTG 的 generative grounding 目标和 Seq2Time 的 sequential knowledge transfer。实验可在 Ego4D-NLQ、LongVideoBench、ActivityNet Captions 和 QVHighlights 上评估长视频定位、跨数据集泛化和推理链可解释性。

### 引言

MLLM 的兴起使 temporal grounding 出现新的可能：模型可以把视频定位转化为语言可表达的时间推理任务，直接生成 timestamp、解释或中间步骤。然而，通用长视频 temporal grounding 仍面临明显瓶颈。Universal VTG 指出，长视频输入受短上下文窗口和高显存需求限制，数万 token 的视频很难直接送入模型；Seq2Time 和 TimeRefine 也指出，现有视频 LLM 缺少高质量 temporal supervision，且 timestamp regression 与传统文本预测目标存在错位。

这些问题说明，仅靠扩大上下文窗口并不能解决长视频定位。模型需要先学会时间关系：哪些片段是前置条件，哪些片段是结果，哪些片段只是背景共现，哪些片段构成事件边界。LocVTP 中的 context warping pretext task 为此提供了一个方向，即通过构造上下文扭曲任务，让模型学习 temporal relation reasoning，而不是只学习局部视觉-文本匹配。

本文主张将 context warping 升级为面向 generative VTG 的预训练范式。模型在预训练时接受被打乱、压缩、重复或局部遮蔽的视频上下文，并需要恢复事件顺序、持续时间和查询相关边界。在推理时，模型不直接处理全部帧 token，而是生成多尺度时间摘要，再通过显式时间链逐步缩小候选区间。

该方向的潜在贡献在于把“长视频 token 压缩”与“显式时间推理能力”连接起来。相比普通 frame sampling，context warping 预训练可以让模型理解时间结构；相比纯 LLM timestamp generation，显式时间链可以提供可检查的中间证据。后续实验应重点验证长视频长度增加时性能下降是否更慢，以及推理链是否能提高边界稳定性。

---

## Idea 6：面向跨域视频时序定位的实体证据路由与去偏校准

对应图谱：FI011，score 9.72，目标问题 MP0123，方法来源 MM0210。  
证据论文包括：EVIDENT、SlotVTG、Embracing Uncertainty。

### 摘要

跨域视频时序定位的难点不只是视觉分布变化，还包括 source-domain fine-tuning 中形成的 temporal location bias、query text bias 和 appearance bias。EVIDENT 指出现有方法容易依赖源域特定模式，而没有继承 MLLM 的 domain-agnostic entity attention；SlotVTG 也强调 object-centric adapter 对泛化的重要性。本文提出实体证据路由与去偏校准框架：模型先从查询中抽取实体、动作和关系槽，再把视觉证据路由到对应实体槽，最后通过去偏校准机制区分 domain-invariant evidence 与 source-specific shortcut。方法吸收 DeNet 中 relation feature / modified feature 解耦和 de-bias prediction 的思想。实验可在 Charades-STA、ActivityNet Captions、QVHighlights 以及跨域设置上验证，重点报告 source-to-target transfer、entity evidence consistency 和 shortcut sensitivity。

### 引言

视频时序定位模型常在特定数据集上训练，再迁移到新的应用域。但不同数据集在视频类型、查询风格、时间分布和视觉对象上差异很大。直接 fine-tune 可能获得较高源域性能，却把源域偏置编码进模型。例如某些动作在源域中常出现在固定时间段，某些查询词与特定背景强相关，某些对象外观在目标域中发生变化。

EVIDENT 提出一个重要观察：跨域失败并不只是 feature distribution shift，而是模型学习到了 source-specific patterns，导致定位知识没有继承 MLLM 本身较强的 domain-agnostic entity attention。SlotVTG 则从 object-centric adapter 角度说明，实体级表征对泛化非常关键。换言之，模型应把“person、door、cup、running”等实体和动作作为证据路由中心，而不是让全局视频特征直接与查询句子对齐。

DeNet 和 Embracing Uncertainty 提供了处理偏置的早期思路。其 relation feature / modified feature 解耦思想可以被重新解释为：一部分特征表达查询中稳定的关系证据，另一部分特征表达主观、风格化或域相关变化。若把这种解耦引入 MLLM adaptation，就可以建立 entity-grounded evidence routing，并对每条证据路径进行不确定性校准。

本文主张跨域 VTG 应从“整体视频-句子对齐”转向“实体证据路由”。模型先解析查询中的实体、动作和关系，再在视频中寻找可支持这些槽位的片段证据。若某个预测主要依赖源域位置先验或背景共现，而非实体证据，则通过 de-bias calibration 降低置信度。该方向适合构造跨域 stress test，并有望在 generalizable VTG 上形成清晰贡献。

---

## Idea 7：面向多干扰视频检索的证据充分性与忠实性评估

对应图谱：FI016，score 9.53，目标问题 MP0082，方法来源 MM0057。  
证据论文包括：A New Framework for Evaluating Faithfulness of Video Moment Retrieval against Multiple Distractors、MVMR、Adaptive Evidential Learning。

### 摘要

现有 VMR 评估通常假设视频中存在正确 moment，并主要衡量预测边界与标注边界的重叠。然而，在包含多个 distractor videos 或误导性上下文的场景中，模型可能对错误视频中的片段给出高置信定位，形成忠实性问题。本文提出面向多干扰视频检索的证据充分性与忠实性评估框架：模型不仅需要输出 moment，还需判断当前视频是否包含足够证据支持查询，并在证据不足时拒绝或降低置信度。方法结合 MVMR 的 multiple distractor setting 和 evidential uncertainty 的 calibration 机制，建立 evidence sufficiency score、faithfulness risk 和 abstention-aware retrieval 指标。实验可在 TACoS、ActivityNet Captions 和构造的 multi-video distractor benchmark 上验证。

### 引言

VMR 模型的标准评估往往关注单个视频内部的边界准确性。但真实检索场景通常更复杂：系统可能面对多个候选视频，其中部分视频与查询共享对象、背景或动作词，却并不包含目标事件。如果模型只能在每个视频中强制选择最高分片段，就可能在 distractor video 上生成看似合理但实际不忠实的答案。

MVMR 和相关 faithfulness evaluation 工作指出，若模型训练时没有考虑给定上下文中的 overconfidence，它可能优先从错误视频中选择一个片段，产生 Type 1 error。这类错误与普通定位偏差不同：即使边界看起来清晰，模型也没有证据说明该视频真的支持查询。因此，faithfulness 需要评估“模型是否知道证据不足”，而不仅是“在标注视频中是否定位准确”。

Adaptive Evidential Learning 提供了可迁移的解决机制。通过 evidential uncertainty、query reconstruction 和 Geom regularizer，模型可以估计预测是否与证据质量匹配。若模型在 distractor video 上只能找到局部词汇匹配或背景共现，应输出高不确定性或 abstention，而不是高置信边界。

本文主张将 evidence sufficiency 作为 VMR 的新评估维度。具体而言，模型对每个候选视频生成定位结果、证据充分性分数和拒识概率；评估时同时计算 accepted correct localization、false acceptance on distractors 和 calibration error。这个方向不一定要求设计庞大新模型，反而可以通过评估协议和轻量校准模块形成清晰论文贡献。

---

## Idea 8：面向弱监督定位的语义负样本重构差异挖掘

对应图谱：FI026，score 9.43，目标问题 MP0059，方法来源 MM0060。  
证据论文包括：Multi-proposal Collaboration and Multi-task Training for Weakly-supervised VMR、Weakly Supervised Video Moment Localization with Contrastive Negative Sample Mining、AuViRe、VLG-Net。

### 摘要

弱监督视频时序定位常利用视频级文本监督或跨视频负样本进行对比学习，但许多方法只区分来自不同视频的 matched / unmatched pairs，忽略同一视频内部不同片段之间更细粒度的语义匹配差异。这样会导致模型缺少 within-video hard negative 训练信号。本文提出语义负样本重构差异挖掘框架：给定查询，模型尝试从候选片段重构查询相关语义或跨模态表示，并把重构误差作为片段级语义不一致信号，从而挖掘同一视频内部的 hard negatives。该思路借鉴 AuViRe 中 reconstruction-discrepancy 用于 temporal localization 的机制，并结合 VLG-Net 的 snippet-token matching。实验可在 ActivityNet Captions、MAD、Charades-STA 和弱监督设置上验证，重点报告 hard negative mining 对定位边界和泛化的影响。

### 引言

弱监督 temporal grounding 的吸引力在于减少精确时间边界标注需求。模型通常只有视频级描述或粗粒度配对信息，需要从弱标签中推断查询对应的时间片段。为了训练这种模型，许多方法构造负样本进行对比学习，例如把其他视频中的片段或查询作为 unmatched pairs。

但图谱中的多篇论文指出，这种跨视频负样本并不充分。Weakly Supervised VML with Contrastive Negative Sample Mining 观察到，给定一个查询，负样本若都来自其他视频，会忽略同一视频中 mismatched segments 的困难性；Multi-proposal collaboration 也指出，同一视频内部的错误片段可能比其他视频的片段更难区分。这说明弱监督定位需要更细粒度的语义负样本，而不是只做视频级配对。

AuViRe 的 reconstruction-discrepancy 思路提供了可迁移机制。在 deepfake temporal localization 中，跨模态重构误差可以成为 frame-level 异常线索。类比到弱监督 VMR，如果一个候选片段无法重构查询中关键动作、对象或关系，它就可能是 query-conditioned hard negative；如果它能重构部分语义但缺少关键关系，则应作为更难的细粒度负样本。

本文主张用重构差异挖掘同视频语义负样本。模型从候选片段生成 query-conditioned representation，并计算与原查询或查询槽位的重构差异。训练时不仅拉近正片段，还按重构差异构造 easy、medium、hard negatives。这样可以让弱监督模型学习片段级语义边界，减少只依赖视频级共现的 shortcut。

---

## Idea 9：面向弱监督长视频定位的因果高斯边界优化

对应图谱：FI037，score 9.34，目标问题 MP0080，方法来源 MM0164。  
证据论文包括：Finding Optimal Video Moment without Training: Gaussian Boundary Optimization、Towards Long-Form Spatio-Temporal Video Grounding、Beyond Uncertainty、Curriculum Multi-Negative Augmentation。

### 摘要

弱监督视频 grounding 中，许多方法依赖 proposal ranking 或启发式边界映射，难以保证预测边界最优，尤其在长视频、多候选片段和稀疏监督场景下更容易陷入局部最优。Gaussian Boundary Optimization 提出无需训练的边界优化思想，说明边界预测可以被看作对候选时间分布的原则性优化；另一方面，因果推断式边界先验可以帮助模型减少 annotation bias 和 proposal dependency。本文提出因果高斯边界优化框架：先用高斯分布表示候选 moment 的起止边界不确定性，再利用因果先验区分查询证据、上下文偏置和 proposal 生成偏置，最后通过可微或后处理优化获得更稳健边界。实验可在 QVHighlights、Charades-STA、ActivityNet Captions 和弱监督设置上验证，重点分析无需额外训练时的泛化、长视频边界稳定性和 annotation bias 抵抗能力。

### 引言

在弱监督 temporal grounding 中，边界预测通常比全监督设置更困难。模型缺少精确起止时间，只能从视频级描述、proposal 分数或伪标签中推断 moment。许多方法因此采用候选 proposal、ranking 或启发式映射，把片段分数转化为最终边界。然而，proposal 结构和映射函数本身可能限制最终性能，即使模型找到了相关区域，也未必能得到最优边界。

Gaussian Boundary Optimization 指出，预定义映射无法充分利用 proposal 中的结构信息，也不能保证最优结果。它尝试用高斯边界优化在不重新训练模型的情况下寻找更合理 moment。这一点对弱监督和长视频特别有价值，因为长视频中候选区间多、边界噪声大，重新训练大型模型成本高。

另一方面，Curriculum Multi-Negative Augmentation 和相关 debiasing 工作说明，temporal annotation bias 会影响模型泛化。边界不应只由 proposal 分数决定，还应考虑该分数是否来自真实查询证据，还是来自视频位置、上下文共现或数据集偏置。因果 prior 可以将 query evidence、context bias 和 proposal bias 分开建模。

本文主张把 GBO 与因果边界先验结合起来。模型或后处理模块把每个候选 moment 表示为边界分布，并通过 do-style adjustment 或 prior correction 校正由上下文和 proposal 结构引入的偏置。该方向的优势是可作为训练无关模块接入多个现有 weakly-supervised VMR 模型，从而形成低成本、强泛化的边界优化论文。

---

## Idea 10：面向上下文增强训练的查询相关内容替换与假负样本修复

对应图谱：FI048，score 9.25，目标问题 MP0047，方法来源 MM0060。  
证据论文包括：CVA、Towards Diverse Temporal Grounding under Single Positive Labels、AuViRe、VLG-Net。

### 摘要

上下文增强是提升 temporal grounding 鲁棒性的常用策略，但若替换片段与查询仍然语义相关，query-agnostic content mixing 会把潜在正样本错误标为负样本，造成 false negative supervision。CVA 通过 video-text similarity replacement pool 缓解这一问题，但仍可进一步建模替换内容与查询之间的细粒度一致性。本文提出查询相关内容替换与假负样本修复框架：在生成增强样本前，模型利用重构差异检测替换片段是否能解释查询关键语义；若替换片段与查询相关，则不直接作为负样本，而是进入 soft label、multi-positive 或 uncertainty-weighted training。该方法可减少上下文增强中的矛盾监督。实验可基于 CVA 在 Charades-STA、QVHighlights 和 ActivityNet Captions 上开展，重点分析 false negative rate、context robustness 和 boundary consistency。

### 引言

为了提升 temporal grounding 的上下文鲁棒性，研究者常对视频上下文进行替换、混合或增强。直觉上，如果目标 moment 保持不变，而背景或周围片段被替换，模型就应学习到更稳定的查询相关表征。然而，这一策略存在隐含风险：被替换的片段可能仍与查询语义相关，甚至包含相似动作或对象。若训练过程把它当作负样本，就会产生假负监督。

CVA 明确指出 query-agnostic mixing 可能造成 false negative，并构建 video-text similarity-based replacement pool 来模拟多样上下文，同时避免无关替换带来的错误负样本。Towards Diverse Temporal Grounding under Single Positive Labels 也指出，单正标签设置下 false negatives 会损害模型泛化。这些观察说明，增强策略必须理解查询，而不能只随机替换片段。

AuViRe 的 reconstruction-discrepancy 机制启发我们用“能否重构查询相关语义”来判断替换片段是否真的是负样本。如果一个替换片段能够重构查询中的动作或对象关系，它就不应被硬标为负；如果它只匹配背景或静态对象，则可以作为 hard negative。相比单纯相似度阈值，重构差异可以提供更细粒度的语义一致性信号。

本文主张在上下文增强前加入 query-aware false-negative repair。系统先评估候选替换片段与查询之间的重构差异和不确定性，再决定其标签策略：明确无关片段作为负样本，语义相关片段作为 soft positive 或 ambiguous sample，证据不足片段降低训练权重。该方向能够直接服务于 CVA 类 context-aware 方法，并提供清晰的消融实验。

---

## 推荐优先级

| 优先级 | 题目 | 推荐理由 |
| --- | --- | --- |
| A | Idea 1：结构化证据链世界模型 | 新问题明显，和长视频、MLLM、token compression、evidence chain 都贴近 2025-2026 趋势，可作为主论文方向。 |
| A | Idea 2：证据校准拒识 | open-set hard-irrelevant query 是新近问题，实验协议清晰，容易形成强动机。 |
| A | Idea 3：边界语义稳定性 | CVA 提供强证据，和 uncertainty calibration 的迁移关系清楚，适合做扎实方法论文。 |
| B | Idea 6：实体证据路由与去偏校准 | 跨域泛化是长期问题，但 entity routing 与 MLLM adaptation 可以形成新切口。 |
| B | Idea 7：证据充分性与忠实性评估 | 可以偏 benchmark/evaluation，也可以做轻量模型，风险较低。 |
| B | Idea 10：假负样本修复 | 和 context augmentation 结合紧密，实验相对可控。 |
| C | Idea 4、5、8、9 | 概念潜力高，但需要更仔细设计方法细节或实验协议，适合作为备选或组合进主方向。 |

## 下一步建议

1. 从 Idea 1、Idea 2、Idea 3 中选择一个作为主攻论文方向。
2. 对选中方向补充 20-30 篇最近两年直接相关论文，并从本地 clean figures/tables 中提取方法图和结果表。
3. 写一版 1 页 research brief：问题定义、方法假设、数据集、baseline、实验矩阵、风险。
4. 预注册最小实验：先做一个 feature-fixed 或 post-processing 版本验证核心假设，再决定是否训练完整模型。
