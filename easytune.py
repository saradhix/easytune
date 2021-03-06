import torch
from torch.utils.data import TensorDataset, random_split, DataLoader, RandomSampler, SequentialSampler

from transformers import AutoTokenizer, AutoModelForSequenceClassification, AdamW
from transformers import get_linear_schedule_with_warmup

from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from tqdm import notebook
import random
import numpy as np
import time
import datetime
import os


def batch(X, batch_size=32):
  total_items  = len(X)
  for ndx in range(0, total_items, batch_size):
    yield X[ndx:min(ndx + batch_size, total_items)]

# Function to calculate the accuracy of our predictions vs labels
def flat_accuracy(preds, labels):
  pred_flat = np.argmax(preds, axis=1).flatten()
  labels_flat = labels.flatten()
  return np.sum(pred_flat == labels_flat) / len(labels_flat)


def format_time(elapsed):
  '''
  Takes a time in seconds and returns a string hh:mm:ss
  '''
  # Round to the nearest second.
  elapsed_rounded = int(round((elapsed)))
  # Format as hh:mm:ss
  return str(datetime.timedelta(seconds=elapsed_rounded))

class Classifier:
  def __init__(self, base_model, num_epochs):
    self.base_model = base_model
    self.model = None
    self.num_epochs = num_epochs
    print("Classifier called with model={}, num_epochs={}".format(base_model, num_epochs))
    #models = ['bert-base-uncased', 'distilbert-base-uncased-finetuned-sst-2-english', 'textattack/roberta-base-SST-2', 'monologg/electra-small-finetuned-imdb', 'google/electra-base-discriminator', 'xlnet-base-cased', 'xlm-roberta-large']
    #if base_model not in models:
    #  print("{} model is not yet supported".format(base_model))
    self.tokenizer = AutoTokenizer.from_pretrained(base_model)
    self.test_size = 0.1
    self.MAX_LENGTH = 64

  def fit(self, X_raw_all, y_all):
    # If there's a GPU available...
    if torch.cuda.is_available():    

      # Tell PyTorch to use the GPU.    
      device = torch.device("cuda")

      print('There are %d GPU(s) available.' % torch.cuda.device_count())
      print('We will use the GPU:', torch.cuda.get_device_name(0))

    # If not...
    else:
      print('No GPU available, using the CPU instead.')
      device = torch.device("cpu")
    pass
    input_ids, attention_masks = self.tokenize(X_raw_all)
    
    # Convert the lists into tensors.
    input_ids = torch.cat(input_ids, dim=0)
    attention_masks = torch.cat(attention_masks, dim=0)
    labels = torch.tensor(y_all)
    print(labels.shape)
    print(input_ids.shape)
    
    train_inputs, validation_inputs, train_labels, validation_labels = train_test_split(input_ids, labels, 
                                                            random_state=42, test_size=self.test_size)

    train_masks, validation_masks, _, _ = train_test_split(attention_masks, labels, 
                                             random_state=42, test_size=self.test_size)
    # Convert all inputs and labels into torch tensors, the required datatype 
# for our model.
    train_inputs = torch.tensor(train_inputs)
    validation_inputs = torch.tensor(validation_inputs)

    train_labels = torch.tensor(train_labels)
    validation_labels = torch.tensor(validation_labels)

    train_masks = torch.tensor(train_masks)
    validation_masks = torch.tensor(validation_masks)
    # The DataLoader needs to know our batch size for training, so we specify it 
# here.
# For fine-tuning BERT on a specific task, the authors recommend a batch size of
# 16 or 32.

    batch_size = 32

    # Create the DataLoader for our training set.
    train_data = TensorDataset(train_inputs, train_masks, train_labels)
    train_sampler = RandomSampler(train_data)
    train_dataloader = DataLoader(train_data, sampler=train_sampler, batch_size=batch_size)

    # Create the DataLoader for our validation set.
    validation_data = TensorDataset(validation_inputs, validation_masks, validation_labels)
    validation_sampler = SequentialSampler(validation_data)
    validation_dataloader = DataLoader(validation_data, sampler=validation_sampler, batch_size=batch_size)
    # Load BertForSequenceClassification, the pretrained BERT model with a single 
# linear classification layer on top. 
    #config = AutoConfig.from_pretrained(self.base_model)
    #model = AutoModelForSequenceClassification.from_config(config)
    model = AutoModelForSequenceClassification.from_pretrained(
    self.base_model, 
    num_labels = 2, # You can increase this for multi-class tasks.   
    output_attentions = False, # Whether the model returns attentions weights.
    output_hidden_states = False, # Whether the model returns all hidden-states.
)

    # Tell pytorch to run this model on the GPU.
    model.cuda()
    # Note: AdamW is a class from the huggingface library (as opposed to pytorch) 
# I believe the 'W' stands for 'Weight Decay fix"
    optimizer = AdamW(model.parameters(),
                  lr = 2e-5, # args.learning_rate - default is 5e-5, our notebook had 2e-5
                  eps = 1e-8 # args.adam_epsilon  - default is 1e-8.
                )
    # Number of training epochs (authors recommend between 2 and 4)
    

    # Total number of training steps is number of batches * number of epochs.
    total_steps = len(train_dataloader) * self.num_epochs

    # Create the learning rate scheduler.
    scheduler = get_linear_schedule_with_warmup(optimizer, 
                                            num_warmup_steps = 0, # Default value in run_glue.py
                                            num_training_steps = total_steps)
    # Set the seed value all over the place to make this reproducible.
    seed_val = 42

    random.seed(seed_val)
    np.random.seed(seed_val)
    torch.manual_seed(seed_val)
    torch.cuda.manual_seed_all(seed_val)

    # Store the average loss after each epoch so we can plot them.
    loss_values = []

    # For each epoch...
    for epoch_i in range(0, self.num_epochs):
    
    # ========================================
    #               Training
    # ========================================
    
    # Perform one full pass over the training set.

      #print("")
      #print('======== Epoch {:} / {:} ========'.format(epoch_i + 1, self.num_epochs))
      #print('Training...')
      description = "Epoch {}/{}   ".format(epoch_i +1, self.num_epochs)

    # Measure how long the training epoch takes.
      t0 = time.time()

    # Reset the total loss for this epoch.
      total_loss = 0

    # Put the model into training mode. Don't be mislead--the call to 
    # `train` just changes the *mode*, it doesn't *perform* the training.
    # `dropout` and `batchnorm` layers behave differently during training
    # vs. test (source: https://stackoverflow.com/questions/51433378/what-does-model-train-do-in-pytorch)
      model.train()

    # For each batch of training data...
      for step, batch in notebook.tqdm(enumerate(train_dataloader), total=len(train_dataloader), desc=description):

        # Progress update every 40 batches.
        if step % 40 == 0 and not step == 0:
          # Calculate elapsed time in minutes.
          elapsed = format_time(time.time() - t0)
            
          # Report progress.
          #print('  Batch {:>5,}  of  {:>5,}.    Elapsed: {:}.'.format(step, len(train_dataloader), elapsed))

        # Unpack this training batch from our dataloader. 
        #
        # As we unpack the batch, we'll also copy each tensor to the GPU using the 
        # `to` method.
        #
        # `batch` contains three pytorch tensors:
        #   [0]: input ids 
        #   [1]: attention masks
        #   [2]: labels 
        b_input_ids = batch[0].to(device)
        b_input_mask = batch[1].to(device)
        b_labels = batch[2].to(device)

        # Always clear any previously calculated gradients before performing a
        # backward pass. PyTorch doesn't do this automatically because 
        # accumulating the gradients is "convenient while training RNNs". 
        # (source: https://stackoverflow.com/questions/48001598/why-do-we-need-to-call-zero-grad-in-pytorch)
        model.zero_grad()        

        # Perform a forward pass (evaluate the model on this training batch).
        # This will return the loss (rather than the model output) because we
        # have provided the `labels`.
        # The documentation for this `model` function is here: 
        # https://huggingface.co/transformers/v2.2.0/model_doc/bert.html#transformers.BertForSequenceClassification
        outputs = model(b_input_ids, 
                    token_type_ids=None, 
                    attention_mask=b_input_mask, 
                    labels=b_labels)
        
        # The call to `model` always returns a tuple, so we need to pull the 
        # loss value out of the tuple.
        loss = outputs[0]

        # Accumulate the training loss over all of the batches so that we can
        # calculate the average loss at the end. `loss` is a Tensor containing a
        # single value; the `.item()` function just returns the Python value 
        # from the tensor.
        total_loss += loss.item()

        # Perform a backward pass to calculate the gradients.
        loss.backward()

        # Clip the norm of the gradients to 1.0.
        # This is to help prevent the "exploding gradients" problem.
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)

        # Update parameters and take a step using the computed gradient.
        # The optimizer dictates the "update rule"--how the parameters are
        # modified based on their gradients, the learning rate, etc.
        optimizer.step()

        # Update the learning rate.
        scheduler.step()

    # Calculate the average loss over the training data.
      avg_train_loss = total_loss / len(train_dataloader)            
    
    # Store the loss value for plotting the learning curve.
      loss_values.append(avg_train_loss)

      #print("")
      print("  Average training loss: {0:.2f} in {1}".format(avg_train_loss,format_time(time.time() - t0)))
      #print("  Training epcoh took: {:}".format(format_time(time.time() - t0)))
        
    # ========================================
    #               Validation
    # ========================================
    # After the completion of each training epoch, measure our performance on
    # our validation set.

      #print("")
      #print("Running Validation...")

      t0 = time.time()

    # Put the model in evaluation mode--the dropout layers behave differently
    # during evaluation.
      model.eval()

    # Tracking variables 
      eval_loss, eval_accuracy = 0, 0
      nb_eval_steps, nb_eval_examples = 0, 0

    # Evaluate data for one epoch
      for batch in validation_dataloader:
        
        # Add batch to GPU
        batch = tuple(t.to(device) for t in batch)
        
        # Unpack the inputs from our dataloader
        b_input_ids, b_input_mask, b_labels = batch
        
        # Telling the model not to compute or store gradients, saving memory and
        # speeding up validation
        with torch.no_grad():        

            # Forward pass, calculate logit predictions.
            # This will return the logits rather than the loss because we have
            # not provided labels.
            # token_type_ids is the same as the "segment ids", which 
            # differentiates sentence 1 and 2 in 2-sentence tasks.
            # The documentation for this `model` function is here: 
            # https://huggingface.co/transformers/v2.2.0/model_doc/bert.html#transformers.BertForSequenceClassification
          outputs = model(b_input_ids, 
                            token_type_ids=None, 
                            attention_mask=b_input_mask)
        
        # Get the "logits" output by the model. The "logits" are the output
        # values prior to applying an activation function like the softmax.
        logits = outputs[0]

        # Move logits and labels to CPU
        logits = logits.detach().cpu().numpy()
        label_ids = b_labels.to('cpu').numpy()
        
        # Calculate the accuracy for this batch of test sentences.
        tmp_eval_accuracy = flat_accuracy(logits, label_ids)
        
        # Accumulate the total accuracy.
        eval_accuracy += tmp_eval_accuracy

        # Track the number of batches
        nb_eval_steps += 1

      # Report the final accuracy for this validation run.
      print("Validation Accuracy: {0:.2f} in {1}".format(eval_accuracy/nb_eval_steps,format_time(time.time() - t0)))
      #print("  Validation took: {:}".format(format_time(time.time() - t0)))

    #print("")
    self.model = model
    print("Training complete!")

  def batched_predict(self, X_test, batch_size=32):
    final_preds = []
    for X_batch in notebook.tqdm(batch(X_test, batch_size=batch_size), total=math.ceil(len(X_test)/batch_size)):
      print("Predicting for samples", len(X_batch))
      preds = self.predict(X_batch)
      final_preds.extend(preds)
    return final_preds

  def predict(self, X_test):
    input_ids, attention_masks = self.silent_tokenize(X_test)
    
    # Convert the lists into tensors.
    test_input_ids = torch.cat(input_ids, dim=0).cuda()
    test_attention_masks = torch.cat(attention_masks, dim=0).cuda()
    print("Predictions")
    with torch.no_grad(): 
      outputs = self.model(test_input_ids, token_type_ids=None, attention_mask=test_attention_masks)
    # Get the "logits" output by the model. The "logits" are the output
    # values prior to applying an activation function like the softmax.
    logits = outputs[0]
    logits = logits.detach().cpu().numpy()
    preds = np.argmax(logits, axis=1).flatten()
    return preds
    pass
  def save(self, name):
    # Saving best-practices: if you use defaults names for the model, you can reload it using from_pretrained()

    output_dir = './'+name+'/'

    # Create output directory if needed
    if not os.path.exists(output_dir):
      os.makedirs(output_dir)

    print("Saving model to %s" % output_dir)

    # Save a trained model, configuration and tokenizer using `save_pretrained()`.
    # They can then be reloaded using `from_pretrained()`
    model_to_save = self.model.module if hasattr(self.model, 'module') else self.model  # Take care of distributed/parallel training
    model_to_save.save_pretrained(output_dir)
    self.tokenizer.save_pretrained(output_dir)
    pass
  def tokenize(self, X_raw_all):
    input_ids = []
    attention_masks = []
    for sent in notebook.tqdm(X_raw_all):
      encoded_dict = self.tokenizer.encode_plus(
                        sent,                      # Sentence to encode.
                        truncation=True,
                        add_special_tokens = True, # Add '[CLS]' and '[SEP]'
                        max_length = self.MAX_LENGTH,           # Pad & truncate all sentences.
                        pad_to_max_length = True,
                        return_attention_mask = True,   # Construct attn. masks.
                        return_tensors = 'pt',     # Return pytorch tensors.
                   )
      # Add the encoded sentence to the list.    
      input_ids.append(encoded_dict['input_ids'])
    
      # And its attention mask (simply differentiates padding from non-padding).
      attention_masks.append(encoded_dict['attention_mask'])
    return input_ids, attention_masks
  def silent_tokenize(self, X_raw_all):
    input_ids = []
    attention_masks = []
    for sent in X_raw_all:
      encoded_dict = self.tokenizer.encode_plus(
                        sent,                      # Sentence to encode.
                        truncation=True,
                        add_special_tokens = True, # Add '[CLS]' and '[SEP]'
                        max_length = self.MAX_LENGTH,           # Pad & truncate all sentences.
                        pad_to_max_length = True,
                        return_attention_mask = True,   # Construct attn. masks.
                        return_tensors = 'pt',     # Return pytorch tensors.
                   )
      # Add the encoded sentence to the list.    
      input_ids.append(encoded_dict['input_ids'])
    
      # And its attention mask (simply differentiates padding from non-padding).
      attention_masks.append(encoded_dict['attention_mask'])
    return input_ids, attention_masks
