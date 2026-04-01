import type { Paper } from "@/types/scholar";

export type { Paper };

export const mockPapers: Paper[] = [
  {
    id: "1",
    title: "Attention Is All You Need: Transformer Architecture for Neural Machine Translation",
    authors: ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar", "Jakob Uszkoreit"],
    year: 2017,
    venue: "NeurIPS",
    abstract: "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.",
    aiSummary: "This paper introduces the Transformer architecture, which relies entirely on self-attention mechanisms for sequence-to-sequence tasks, eliminating the need for recurrent or convolutional layers. The model achieves state-of-the-art results on machine translation benchmarks.",
    keywords: ["transformer", "attention", "neural machine translation", "deep learning"],
    citations: 89234,
    sections: [
      { title: "Abstract", content: "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms." },
      { title: "Introduction", content: "Recurrent neural networks, long short-term memory and gated recurrent neural networks in particular, have been firmly established as state of the art approaches in sequence modeling and transduction problems such as language modeling and machine translation." },
      { title: "Methods", content: "The Transformer follows an encoder-decoder structure using stacked self-attention and point-wise, fully connected layers for both the encoder and decoder. The encoder maps an input sequence of symbol representations to a sequence of continuous representations." },
      { title: "Results", content: "On the WMT 2014 English-to-German translation task, the big transformer model outperforms the best previously reported models including ensembles by more than 2.0 BLEU, establishing a new state-of-the-art BLEU score of 28.4." },
      { title: "Conclusion", content: "In this work, we presented the Transformer, the first sequence transduction model based entirely on attention, replacing the recurrent layers most commonly used in encoder-decoder architectures with multi-headed self-attention." },
      { title: "References", content: "1. Bahdanau et al. Neural Machine Translation by Jointly Learning to Align and Translate. 2015\n2. Sutskever et al. Sequence to Sequence Learning with Neural Networks. 2014" }
    ]
  },
  {
    id: "2",
    title: "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding",
    authors: ["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee", "Kristina Toutanova"],
    year: 2019,
    venue: "NAACL",
    abstract: "We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers. BERT is designed to pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both left and right context in all layers.",
    aiSummary: "BERT revolutionizes NLP by introducing bidirectional pre-training of transformers. By training on masked language modeling and next sentence prediction, BERT learns rich contextual representations that transfer effectively to downstream tasks.",
    keywords: ["BERT", "pre-training", "language model", "NLP", "transformers"],
    citations: 67543,
    sections: [
      { title: "Abstract", content: "We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers." },
      { title: "Introduction", content: "Language model pre-training has been shown to be effective for improving many natural language processing tasks. These include sentence-level tasks such as natural language inference and paraphrasing." },
      { title: "Methods", content: "BERT's model architecture is a multi-layer bidirectional Transformer encoder based on the original implementation described in Vaswani et al. We use masked language modeling and next sentence prediction objectives." },
      { title: "Results", content: "BERT obtains new state-of-the-art results on eleven natural language processing tasks, including pushing the GLUE score to 80.5%, MultiNLI accuracy to 86.7%, and SQuAD v2.0 Test F1 to 83.1." },
      { title: "Conclusion", content: "We have introduced BERT, a new language representation model that achieves state-of-the-art performance on a broad range of NLP tasks." },
      { title: "References", content: "1. Vaswani et al. Attention Is All You Need. 2017\n2. Peters et al. Deep contextualized word representations. 2018" }
    ]
  },
  {
    id: "3",
    title: "GPT-4 Technical Report: Large-Scale Multimodal Language Model",
    authors: ["OpenAI Research Team", "Sam Altman", "Greg Brockman"],
    year: 2023,
    venue: "arXiv",
    abstract: "We report the development of GPT-4, a large-scale, multimodal model which can accept image and text inputs and produce text outputs. GPT-4 exhibits human-level performance on various professional and academic benchmarks.",
    aiSummary: "GPT-4 represents a significant advancement in large language models, capable of processing both text and images. It demonstrates remarkable performance on standardized tests and professional benchmarks, approaching or exceeding human-level accuracy.",
    keywords: ["GPT-4", "multimodal", "large language model", "AI safety", "OpenAI"],
    citations: 12456,
    sections: [
      { title: "Abstract", content: "We report the development of GPT-4, a large-scale, multimodal model which can accept image and text inputs and produce text outputs." },
      { title: "Introduction", content: "This technical report presents GPT-4, a large multimodal model capable of processing image and text inputs and producing text outputs." },
      { title: "Methods", content: "GPT-4 is a Transformer-based model pre-trained to predict the next token in a document. The model was then fine-tuned using Reinforcement Learning from Human Feedback (RLHF)." },
      { title: "Results", content: "GPT-4 passes a simulated bar exam with a score around the top 10% of test takers. On the AP exams, GPT-4 achieves passing scores on a majority of subjects." },
      { title: "Conclusion", content: "GPT-4 represents a step forward in AI capability, demonstrating human-level performance across a range of academic and professional benchmarks." },
      { title: "References", content: "1. Brown et al. Language Models are Few-Shot Learners. 2020\n2. Ouyang et al. Training language models to follow instructions. 2022" }
    ]
  },
  {
    id: "4",
    title: "ImageNet Classification with Deep Convolutional Neural Networks",
    authors: ["Alex Krizhevsky", "Ilya Sutskever", "Geoffrey E. Hinton"],
    year: 2012,
    venue: "NeurIPS",
    abstract: "We trained a large, deep convolutional neural network to classify the 1.2 million high-resolution images in the ImageNet LSVRC-2010 contest into the 1000 different classes.",
    aiSummary: "This landmark paper introduced AlexNet, demonstrating that deep convolutional neural networks could dramatically outperform traditional computer vision methods on large-scale image classification tasks.",
    keywords: ["CNN", "image classification", "deep learning", "ImageNet", "AlexNet"],
    citations: 98234,
    sections: [
      { title: "Abstract", content: "We trained a large, deep convolutional neural network to classify the 1.2 million high-resolution images in the ImageNet LSVRC-2010 contest." },
      { title: "Introduction", content: "Current approaches to object recognition make essential use of machine learning methods. To improve their performance, we can collect larger datasets, learn more powerful models, and use better techniques for preventing overfitting." },
      { title: "Methods", content: "The neural network, which has 60 million parameters and 650,000 neurons, consists of five convolutional layers, some of which are followed by max-pooling layers, and three fully-connected layers." },
      { title: "Results", content: "We achieved top-1 and top-5 error rates of 37.5% and 17.0% which is considerably better than the previous state-of-the-art." },
      { title: "Conclusion", content: "Our results show that a large, deep convolutional neural network is capable of achieving record-breaking results on a highly challenging dataset using purely supervised learning." },
      { title: "References", content: "1. LeCun et al. Backpropagation Applied to Handwritten Zip Code Recognition. 1989\n2. Simard et al. Best Practices for Convolutional Neural Networks. 2003" }
    ]
  },
  {
    id: "5",
    title: "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
    authors: ["Patrick Lewis", "Ethan Perez", "Aleksandra Piktus", "Fabio Petroni"],
    year: 2020,
    venue: "NeurIPS",
    abstract: "Large pre-trained language models have been shown to store factual knowledge in their parameters, and achieve state-of-the-art results when fine-tuned on downstream NLP tasks. We explore a general-purpose fine-tuning recipe for retrieval-augmented generation.",
    aiSummary: "RAG combines the benefits of retrieval-based and generation-based approaches. By retrieving relevant documents during generation, the model can access up-to-date information and provide more accurate, grounded responses.",
    keywords: ["RAG", "retrieval", "generation", "knowledge base", "NLP"],
    citations: 5678,
    sections: [
      { title: "Abstract", content: "We explore a general-purpose fine-tuning recipe for retrieval-augmented generation (RAG) — models which combine pre-trained parametric and non-parametric memory for language generation." },
      { title: "Introduction", content: "Large pre-trained language models have been shown to store a surprising amount of factual knowledge in their parameters, achieving impressive results on knowledge-intensive NLP tasks." },
      { title: "Methods", content: "RAG models combine pre-trained seq2seq models with a differentiable retriever. We use a bi-encoder architecture where documents and queries are independently encoded." },
      { title: "Results", content: "RAG achieves state-of-the-art results on open-domain question answering benchmarks and generates more specific, diverse and factual text than state-of-the-art seq2seq models." },
      { title: "Conclusion", content: "We have presented RAG, a general-purpose fine-tuning recipe that combines retrieval with generation, enabling language models to access vast knowledge bases." },
      { title: "References", content: "1. Karpukhin et al. Dense Passage Retrieval for Open-Domain Question Answering. 2020\n2. Lewis et al. BART: Denoising Sequence-to-Sequence Pre-training. 2020" }
    ]
  },
  {
    id: "6",
    title: "Scaling Laws for Neural Language Models",
    authors: ["Jared Kaplan", "Sam McCandlish", "Tom Henighan", "Tom B. Brown"],
    year: 2020,
    venue: "arXiv",
    abstract: "We study empirical scaling laws for language model performance on the cross-entropy loss. The loss scales as a power-law with model size, dataset size, and the amount of compute used for training.",
    aiSummary: "This influential paper establishes mathematical relationships between model performance and key factors like model size, data size, and compute budget, providing crucial insights for efficiently scaling language models.",
    keywords: ["scaling laws", "language models", "compute", "power law", "training"],
    citations: 4532,
    sections: [
      { title: "Abstract", content: "We study empirical scaling laws for language model performance on the cross-entropy loss." },
      { title: "Introduction", content: "Language modeling has emerged as a powerful approach to learning general purpose representations from text." },
      { title: "Methods", content: "We trained a wide range of Transformer language models varying in size from 768 to 1.5 billion parameters, on datasets ranging from 22 million to 23 billion tokens." },
      { title: "Results", content: "We find that test loss scales as a power-law in each of model size, dataset size, and amount of compute, with each contributing independently." },
      { title: "Conclusion", content: "Our scaling laws provide predictable relationships between compute, data, model size, and performance, enabling efficient resource allocation for training large language models." },
      { title: "References", content: "1. Radford et al. Language Models are Unsupervised Multitask Learners. 2019\n2. Brown et al. Language Models are Few-Shot Learners. 2020" }
    ]
  }
];

export const mockChatHistory = [
  {
    id: "1",
    role: "user" as const,
    content: "What is the main contribution of the Transformer paper?",
    timestamp: new Date("2024-01-15T10:30:00"),
  },
  {
    id: "2",
    role: "assistant" as const,
    content: "The main contribution of the \"Attention Is All You Need\" paper is introducing the Transformer architecture, which relies entirely on self-attention mechanisms for sequence-to-sequence tasks. Key innovations include:\n\n1. **Multi-head self-attention**: Allows the model to attend to different positions simultaneously\n2. **Positional encoding**: Enables the model to understand sequence order without recurrence\n3. **Parallel processing**: Unlike RNNs, Transformers can process all positions simultaneously\n\n[Source: Vaswani et al., 2017, Section 3.2]",
    timestamp: new Date("2024-01-15T10:30:15"),
    citations: ["Attention Is All You Need, Section 3.2"],
  },
];
